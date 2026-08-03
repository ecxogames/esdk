"""Disposable Docker development runner and in-container ESDK test command."""

import compileall
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCKERFILE = os.path.join(BASE_DIR, "Dockerfile.esdk")
IMAGE_NAME = "esdk-app-test"


def silent_process_options():
    """Hide Docker CLI/Desktop process windows while retaining captured output."""
    options = {}
    if sys.platform == "win32":
        options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE
        options["startupinfo"] = startupinfo
    return options


def run_with_progress(command, label, cwd):
    """Run a Docker command behind a compact, indeterminate progress bar."""
    started_at = time.monotonic()
    interactive = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as output:
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=output,
                stderr=subprocess.STDOUT,
                text=True,
                **silent_process_options(),
            )
        except OSError as error:
            print(f"[Error] {label} could not be started: {error}")
            return 1

        width = 28
        position = 0
        direction = 1
        if not interactive:
            print(f"[Docker] {label}...")

        while process.poll() is None:
            if interactive:
                marker_width = 6
                bar = [" "] * width
                for index in range(position, min(position + marker_width, width)):
                    bar[index] = "="
                elapsed = int(time.monotonic() - started_at)
                print(f"\r[Docker] {label} [{''.join(bar)}] {elapsed:>3}s", end="", flush=True)

                position += direction
                if position >= width - marker_width or position <= 0:
                    direction *= -1
            time.sleep(0.15)

        elapsed = int(time.monotonic() - started_at)
        if interactive:
            status_bar = "=" * width if process.returncode == 0 else "!" * width
            print(f"\r[Docker] {label} [{status_bar}] {elapsed:>3}s")

        if process.returncode == 0:
            if not interactive:
                print(f"[Docker] {label} complete ({elapsed}s).")
            return 0

        print(f"[Error] {label} failed. Docker output follows:")
        output.seek(0)
        docker_output = output.read().strip()
        if docker_output:
            print(docker_output)
        return process.returncode


def find_docker_executable():
    discovered = shutil.which("docker")
    if discovered:
        return discovered

    candidates = []
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
    return next((candidate for candidate in candidates if os.path.isfile(candidate)), None)


def find_docker_desktop_executable():
    candidates = []
    for base in (os.environ.get("ProgramW6432"), os.environ.get("PROGRAMFILES"), os.environ.get("LOCALAPPDATA")):
        if base:
            candidates.append(os.path.join(base, "Docker", "Docker", "Docker Desktop.exe"))
    return next((candidate for candidate in dict.fromkeys(candidates) if os.path.isfile(candidate)), None)


def docker_engine_is_ready(docker_cli):
    try:
        result = subprocess.run(
            [docker_cli, "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            **silent_process_options(),
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def ensure_docker_engine(docker_cli, timeout_seconds=180):
    """Start Docker Desktop when necessary and wait for its API to become ready."""
    if docker_engine_is_ready(docker_cli):
        return True

    if sys.platform != "win32":
        print("[Error] The Docker engine is not running. Start it and try again.")
        return False

    print("[Docker] Docker engine is stopped. Starting Docker Desktop...")
    try:
        # The supported Desktop CLI starts the backend without opening the
        # Dashboard. Older installations fall back to the autostart path.
        desktop_start = subprocess.run(
            [docker_cli, "desktop", "start", "--detach"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            **silent_process_options(),
        )
        if desktop_start.returncode != 0:
            desktop_executable = find_docker_desktop_executable()
            if not desktop_executable:
                print("[Error] Docker Desktop is installed, but its startup command could not be found.")
                return False
            fallback_options = silent_process_options()
            fallback_options["creationflags"] = (
                fallback_options.get("creationflags", 0)
                | getattr(subprocess, "DETACHED_PROCESS", 0)
                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            )
            subprocess.Popen(
                [desktop_executable, "-Autostart"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                **fallback_options,
            )
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"[Error] Docker Desktop could not be started: {error}")
        return False

    print(f"[Docker] Waiting up to {timeout_seconds} seconds for the engine to become ready...")
    deadline = time.monotonic() + timeout_seconds
    next_update = time.monotonic() + 15
    while time.monotonic() < deadline:
        if docker_engine_is_ready(docker_cli):
            print("[Docker] Docker Desktop is ready.")
            return True
        if time.monotonic() >= next_update:
            print("[Docker] Still waiting for Docker Desktop...")
            next_update = time.monotonic() + 15
        time.sleep(2)

    print("[Error] Docker Desktop did not become ready before the timeout.")
    print("[Error] Check Docker Desktop for first-run agreements, WSL 2, virtualization, or restart requests.")
    return False


def run_container_tests():
    """Validate the app backend from inside the disposable container."""
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

    print("[Test] Compiling Python application sources...")
    source_dirs = [path for path in ("server", "public", "private") if os.path.isdir(path)]
    if not all(compileall.compile_dir(path, quiet=1) for path in source_dirs):
        return 1

    print("[Test] Importing the backend entry point...")
    __import__("server.api")

    if not os.path.isdir("tests"):
        print("[Test] No tests/ directory found; smoke test passed.")
        return 0

    print("[Test] Running unittest discovery...")
    suite = unittest.defaultTestLoader.discover("tests", pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def run_disposable_container():
    """Build the app snapshot and run it once in a new disposable container."""
    if not os.path.exists(DOCKERFILE):
        print("[Error] Docker is not configured. Run: python scripts/setup.py")
        return 1
    docker_cli = find_docker_executable()
    if not docker_cli:
        print("[Error] Docker is not installed or is not available in PATH.")
        print("[Error] Run: python scripts/setup.py and choose Docker setup.")
        return 1
    if not ensure_docker_engine(docker_cli):
        return 1

    build_result = run_with_progress(
        [docker_cli, "build", "-f", DOCKERFILE, "-t", IMAGE_NAME, "."],
        "Building isolated app container",
        BASE_DIR,
    )
    if build_result != 0:
        return build_result

    return run_with_progress(
        [docker_cli, "run", "--rm", IMAGE_NAME],
        "Setting up and validating new container",
        BASE_DIR,
    )


def main(args=None):
    args = sys.argv[1:] if args is None else args
    if "--inside-container" in args:
        return run_container_tests()
    return run_disposable_container()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nDocker run cancelled.")
        sys.exit(130)
