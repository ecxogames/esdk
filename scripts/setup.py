import urllib.request
import os
import subprocess
import sys
import platform
import tempfile
import zipfile
import shutil

try:
    from scripts.requirements import (
        ensure_compatible_interpreter,
        has_installable_requirements,
        read_requirements,
        resolved_python_version,
        write_pip_requirements,
    )
except ImportError:
    from requirements import (
        ensure_compatible_interpreter,
        has_installable_requirements,
        read_requirements,
        resolved_python_version,
        write_pip_requirements,
    )

try:
    from scripts.docker import ensure_docker_engine
except ImportError:
    from docker import ensure_docker_engine

WEBVIEW_HEADER_URL = "https://raw.githubusercontent.com/webview/webview/0.10.0/webview.h"
WEBVIEW2_NUGET_URL = "https://www.nuget.org/api/v2/package/Microsoft.Web.WebView2"

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TARGET_DIR = os.path.join(BASE_DIR, "engine")
TARGET_PATH = os.path.join(TARGET_DIR, "webview.h")
WEBVIEW2_DIR = os.path.join(TARGET_DIR, "webview2")
BUILD_DIR = os.path.join(BASE_DIR, "build")
DOCKERFILE_PATH = os.path.join(BASE_DIR, "Dockerfile.esdk")
DOCKERIGNORE_PATH = os.path.join(BASE_DIR, ".dockerignore")


def ask_yes_no(prompt, default=True):
    suffix = "Y/n" if default else "y/N"
    while True:
        answer = input(f"{prompt} ({suffix}): ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'.")


def docker_cli_candidates():
    candidates = []
    discovered = shutil.which("docker")
    if discovered:
        candidates.append(discovered)

    for base in (
        os.environ.get("ProgramW6432"),
        os.environ.get("PROGRAMFILES"),
        os.environ.get("LOCALAPPDATA"),
    ):
        if not base:
            continue
        if base == os.environ.get("LOCALAPPDATA"):
            candidates.append(os.path.join(base, "Docker", "resources", "bin", "docker.exe"))
        else:
            candidates.append(os.path.join(base, "Docker", "Docker", "resources", "bin", "docker.exe"))
    return list(dict.fromkeys(candidates))


def find_docker_cli():
    return next((candidate for candidate in docker_cli_candidates() if os.path.isfile(candidate)), None)


def add_directory_to_user_path(directory):
    directory = os.path.abspath(directory)
    current_entries = [entry for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]
    if os.path.normcase(directory) not in {os.path.normcase(entry) for entry in current_entries}:
        os.environ["PATH"] = directory + os.pathsep + os.environ.get("PATH", "")

    if platform.system() != "Windows":
        return

    try:
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as environment_key:
            try:
                user_path, _ = winreg.QueryValueEx(environment_key, "Path")
            except FileNotFoundError:
                user_path = ""
            user_entries = [entry for entry in user_path.split(os.pathsep) if entry]
            if os.path.normcase(directory) not in {os.path.normcase(entry) for entry in user_entries}:
                updated_path = os.pathsep.join(user_entries + [directory])
                winreg.SetValueEx(environment_key, "Path", 0, winreg.REG_EXPAND_SZ, updated_path)
                print(f"[+] Added Docker CLI to your user PATH: {directory}")
    except OSError as error:
        print(f"[!] Docker was found, but its directory could not be saved to user PATH: {error}")


def install_docker_desktop():
    if platform.system() != "Windows":
        print("[-] Automatic Docker Desktop installation is currently supported on Windows only.")
        print("[-] Install Docker for your platform, then run setup again.")
        return None

    winget = shutil.which("winget")
    if not winget:
        print("[-] Windows Package Manager (winget) is required to install Docker Desktop automatically.")
        return None

    print("[*] Docker Desktop was not found. Requesting administrator permission...")
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        print("[-] PowerShell is required to launch the Docker Desktop installer as administrator.")
        return None

    escaped_winget = winget.replace("'", "''")
    install_script = (
        f"$p = Start-Process -FilePath '{escaped_winget}' "
        "-ArgumentList @('install','--id','Docker.DockerDesktop','--exact',"
        "'--silent','--accept-package-agreements','--accept-source-agreements') "
        "-Verb RunAs -WindowStyle Hidden -Wait -PassThru; exit $p.ExitCode"
    )
    try:
        hidden_process = {}
        if platform.system() == "Windows":
            hidden_process["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            [
                powershell, "-NoLogo", "-NoProfile", "-NonInteractive",
                "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
                "-Command", install_script,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **hidden_process,
        )
    except subprocess.CalledProcessError as error:
        print(f"[-] Docker Desktop installation failed: {error}")
        return None

    docker_cli = find_docker_cli()
    if not docker_cli:
        print("[!] Docker Desktop finished installing, but docker.exe was not found yet.")
        print("[!] Restart Windows if the installer requested it, then run setup again.")
        return None
    print("[+] Docker Desktop installed successfully.")
    return docker_cli


def ensure_docker_available():
    docker_cli = find_docker_cli() or install_docker_desktop()
    if not docker_cli:
        return None

    add_directory_to_user_path(os.path.dirname(docker_cli))
    return docker_cli


def configure_docker():
    if not ask_yes_no("[?] Set up disposable Docker app tests?", default=False):
        print("[*] Docker development setup skipped.")
        return False

    python_version = resolved_python_version()
    dockerfile = f'''ARG PYTHON_VERSION={python_version}
FROM python:${{PYTHON_VERSION}}-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update \\
    && apt-get install -y --no-install-recommends build-essential tk \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/esdk-requirements.txt
RUN sed -E '/^[[:space:]]*python[[:space:]]*==/Id' /tmp/esdk-requirements.txt > /tmp/pip-requirements.txt \\
    && if [ -s /tmp/pip-requirements.txt ]; then pip install --no-cache-dir -r /tmp/pip-requirements.txt; fi

COPY . .
CMD ["python", "scripts/docker.py", "--inside-container"]
'''
    dockerignore = '''.git
.vscode
build
dist
__pycache__
*.pyc
*.zip
Dockerfile*
'''
    with open(DOCKERFILE_PATH, "w", encoding="utf-8", newline="\n") as docker_file:
        docker_file.write(dockerfile)
    with open(DOCKERIGNORE_PATH, "w", encoding="utf-8", newline="\n") as ignore_file:
        ignore_file.write(dockerignore)

    print("[+] Docker test environment created.")
    docker_cli = ensure_docker_available()
    if docker_cli:
        if ensure_docker_engine(docker_cli):
            print("[+] Docker is installed, on PATH, and its engine is ready.")
            print("[+] Run: python scripts/dev.py, then choose Docker.")
        else:
            print("[!] Docker installed successfully, but its engine is not ready yet.")
            print("[!] Complete any instructions shown by Docker Desktop, then rerun setup.")
    else:
        print("[!] Docker setup could not be completed automatically.")
    return True


def install_python_requirements():
    try:
        python_version = resolved_python_version()
        ensure_compatible_interpreter(python_version)
        _, pip_lines = read_requirements()
    except (ValueError, RuntimeError) as error:
        print(f"[-] {error}")
        sys.exit(1)

    if not has_installable_requirements(pip_lines):
        print("[*] No Python packages listed in requirements.txt.")
        return

    requirements_path = write_pip_requirements(pip_lines)
    try:
        print("[*] Installing Python packages from requirements.txt...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", requirements_path], check=True)
        print("[+] Python packages installed successfully.")
    except subprocess.CalledProcessError as error:
        print(f"[-] Failed to install Python requirements: {error}")
        sys.exit(1)
    finally:
        if os.path.exists(requirements_path):
            os.remove(requirements_path)

def download_webview():
    print(f"[*] Downloading webview.h from {WEBVIEW_HEADER_URL}...")
    try:
        os.makedirs(TARGET_DIR, exist_ok=True)
        urllib.request.urlretrieve(WEBVIEW_HEADER_URL, TARGET_PATH)
        print(f"[+] Successfully downloaded to {TARGET_PATH}")
    except Exception as e:
        print(f"[-] Error downloading webview.h: {e}")
        sys.exit(1)

def download_webview2_headers():
    if platform.system() != "Windows":
        return # WebView2 is Windows-only

    print(f"[*] Downloading Microsoft WebView2 SDK...")
    
    zip_path = os.path.join(tempfile.gettempdir(), "webview2.zip")
    try:
        urllib.request.urlretrieve(WEBVIEW2_NUGET_URL, zip_path)
        
        # Extract only the necessary C++ headers
        os.makedirs(WEBVIEW2_DIR, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.namelist():
                if member.startswith("build/native/include/"):
                    # Extract it while flattening the directory structure
                    filename = os.path.basename(member)
                    if filename: # Skip empty directories
                        source = zip_ref.open(member)
                        target = open(os.path.join(WEBVIEW2_DIR, filename), "wb")
                        with source, target:
                            shutil.copyfileobj(source, target)
        
        print(f"[+] Successfully extracted WebView2 headers to {WEBVIEW2_DIR}")
        os.remove(zip_path)
    except Exception as e:
        print(f"[-] Error downloading/extracting WebView2: {e}")
        sys.exit(1)

def install_cmake():
    print("\n[-] CMake not found in your system's PATH.")
    choice = input("[?] Would you like to automatically download and install CMake now? (Y/n): ")
    if choice.strip().lower() not in ['', 'y', 'yes']:
        print("[-] Please install CMake manually from https://cmake.org/download/ and try again.")
        sys.exit(1)
        
    if platform.system() != "Windows":
        print("[-] Automated installation is currently only supported on Windows.")
        print("[-] Please install via your package manager (e.g., `apt install cmake` or `brew install cmake`).")
        sys.exit(1)
        
    cmake_version = "3.29.3"
    msi_url = f"https://github.com/Kitware/CMake/releases/download/v{cmake_version}/cmake-{cmake_version}-windows-x86_64.msi"
    msi_path = os.path.join(tempfile.gettempdir(), f"cmake-{cmake_version}.msi")
    
    print(f"[*] Downloading CMake {cmake_version} installer... (This might take a minute)")
    try:
        urllib.request.urlretrieve(msi_url, msi_path)
        print("[*] Installing CMake... (Please accept the Administrator privilege prompt if it appears)")
        # /passive shows progress bar, ADD_CMAKE_TO_PATH=System adds it to the system environment variables
        subprocess.run(["msiexec.exe", "/i", msi_path, "ADD_CMAKE_TO_PATH=System", "/passive"], check=True)
        
        # Temporarily append the default installation directory to the current process PATH
        # so that the script can continue right away without requiring a terminal restart.
        os.environ["PATH"] += os.pathsep + r"C:\Program Files\CMake\bin"
        
        print("[+] CMake installation completed successfully.")
    except Exception as e:
        print(f"[-] Failed to install CMake automatically: {e}")
        sys.exit(1)

def configure_cmake():
    print("\n[*] Configuring CMake...")
    os.makedirs(BUILD_DIR, exist_ok=True)
    try:
        subprocess.run(["cmake", ".."], cwd=BUILD_DIR, check=True)
        print("[+] CMake configuration completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[-] Error during CMake configuration: {e}")
        print("Note: On Windows, to compile you will also need the WebView2 SDK. Check the readme for https://github.com/webview/webview")
        sys.exit(1)
    except FileNotFoundError:
        install_cmake()
        print("\n[*] Retrying CMake configuration...")
        try:
            subprocess.run(["cmake", ".."], cwd=BUILD_DIR, check=True)
            print("[+] CMake configuration completed successfully.")
        except Exception as e:
            print(f"[-] Error running CMake after installation. Note: You might need to restart your terminal to refresh the system PATH.")
            sys.exit(1)

def print_instructions():
    print("\n" + "="*55)
    print(" Setup Complete! Here are your next steps:")
    print("="*55)
    print("\n1. Build the project:")
    print("   cd build")
    print("   cmake --build .")
    print("\n2. Run the application:")
    if os.name == 'nt': # Windows
        print("   .\\build\\Debug\\ESDEngine.exe")
    else:
        print("   ./build/ESDEngine")
    if os.path.exists(DOCKERFILE_PATH):
        print("\n3. Run backend tests in a brand-new container:")
        print("   python scripts/dev.py")
        print("   Then answer yes when asked to use Docker.")
    print("\n" + "="*55 + "\n")

if __name__ == "__main__":
    print("Starting ESD Suite Environment Setup...\n")
    configure_docker()
    install_python_requirements()
    download_webview()
    download_webview2_headers()
    configure_cmake()
    print_instructions()
