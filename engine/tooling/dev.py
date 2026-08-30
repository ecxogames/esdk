import os
import stat
import time
import subprocess
import sys
import shutil
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
try:
    from engine.tooling.build import prepare_icon
except ImportError:
    prepare_icon = lambda: None

try:
    from engine.tooling import docker
except ImportError:
    import docker

try:
    from engine.tooling.frontend import compile_frontend
except ImportError:
    from frontend import compile_frontend

WATCH_PATHS = ['engine', 'server', 'ui', 'properties.config', 'requirements.txt', 'package.json', 'CMakeLists.txt']
BUILD_DIR = os.path.join('.edk', 'build')
WEB_DEV_DIR = os.path.join('.edk', 'web-dev')
WEB_REVISION = {'value': 0}

def get_server_port():
    try:
        with open('properties.config', 'r', encoding='utf-8') as config:
            for line in config:
                if line.strip().startswith('APP_PORT='):
                    port = int(line.split('=', 1)[1].strip())
                    if 1 <= port <= 65535:
                        return port
    except (OSError, ValueError):
        pass
    return 2024

def get_exe_path():
    bases = [
        os.path.join(BUILD_DIR, 'Debug', 'EDKEngine.exe'),
        os.path.join(BUILD_DIR, 'Release', 'EDKEngine.exe'),
        os.path.join(BUILD_DIR, 'EDKEngine.exe'),
        os.path.join(BUILD_DIR, 'Debug', 'ESDEngine.exe'),
        os.path.join(BUILD_DIR, 'Release', 'ESDEngine.exe'),
        os.path.join(BUILD_DIR, 'ESDEngine.exe'),
        os.path.join(BUILD_DIR, 'ESDEngine')
    ]
    for b in bases:
        if os.path.exists(b):
            return b
    return None

def get_latest_mtime():
    max_ts = 0
    IGNORE_FILES = {'icon.rc', 'converted_icon.ico'}
    IGNORE_DIRS = {'__pycache__'}

    for path in WATCH_PATHS:
        if not os.path.exists(path):
            continue
        if os.path.isfile(path):
            if os.path.basename(path) not in IGNORE_FILES:
                max_ts = max(max_ts, os.path.getmtime(path))
        else:
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                for f in files:
                    if f in IGNORE_FILES:
                        continue
                    try:
                        max_ts = max(max_ts, os.path.getmtime(os.path.join(root, f)))
                    except FileNotFoundError:
                        pass
    return max_ts

def clean_build():
    if not os.path.exists(BUILD_DIR):
        return
    print("[Dev] Clearing build directory...")
    _stop_build_processes()

    def make_writable_and_retry(function, path, _error_info):
        os.chmod(path, os.stat(path).st_mode | stat.S_IWRITE)
        function(path)

    last_error = None
    for attempt in range(5):
        try:
            shutil.rmtree(BUILD_DIR, onerror=make_writable_and_retry)
            return
        except (OSError, PermissionError) as error:
            last_error = error
            time.sleep(0.4 * (attempt + 1))
    raise RuntimeError(
        f"Unable to clear '{os.path.abspath(BUILD_DIR)}'. Close File Explorer windows "
        "inside the build folder and pause OneDrive sync, then retry."
    ) from last_error


def _stop_build_processes():
    """Stop only EDK processes whose executable lives in this project's build folder."""
    if sys.platform != "win32":
        return
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if not powershell:
        return
    build_root = os.path.abspath(BUILD_DIR)
    script = (
        "$root=[IO.Path]::GetFullPath($env:EDK_BUILD_ROOT).TrimEnd('\\')+'\\';"
        "Get-Process -Name ESDEngine -ErrorAction SilentlyContinue|ForEach-Object{"
        "try{$p=$_.Path}catch{$p=$null};if($p-and[IO.Path]::GetFullPath($p).StartsWith($root,"
        "[StringComparison]::OrdinalIgnoreCase)){Stop-Process -Id $_.Id -Force}}"
    )
    environment = os.environ.copy()
    environment["EDK_BUILD_ROOT"] = build_root
    subprocess.run(
        [powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, timeout=15, env=environment,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    time.sleep(0.3)

def build_project():
    print("[Dev] Building project...")
    try:
        compile_frontend("desktop", optimize=False, quiet=True)
        prepare_icon()
        cache_file = os.path.join(BUILD_DIR, "CMakeCache.txt")
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except OSError:
                pass
        subprocess.run(['cmake', '-B', BUILD_DIR, '-DESD_EMBED_HTML=OFF'], check=True, stdout=subprocess.DEVNULL)
    except Exception as e:
        print(f"[Dev] Warning: pre-build step failed: {e}")

    for attempt in range(3):
        result = subprocess.run(['cmake', '--build', BUILD_DIR])
        if result.returncode == 0:
            return True
        if attempt < 2:
            print(f"[Dev] Build output was locked; retrying ({attempt + 2}/3)...")
            time.sleep(0.75 * (attempt + 1))
    return False

def free_port():
    """Kill any process currently bound to APP_PORT so the new server can bind cleanly."""
    import socket
    server_port = get_server_port()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', server_port)) != 0:
            return  # port already free
    try:
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if f':{server_port}' in line and 'LISTENING' in line:
                parts = line.split()
                pid = parts[-1]
                if pid.isdigit() and pid != '0':
                    subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                    print(f"[Dev] Released port {server_port} (killed PID {pid})")
                    time.sleep(0.3)
                    break
    except Exception as e:
        print(f"[Dev] Warning: could not release port {server_port}: {e}")

def clear_webview_cache():
    """Delete WebView2's persistent disk cache so every launch loads fresh content."""
    exe = get_exe_path()
    candidates = []

    if exe:
        exe_dir = os.path.dirname(os.path.abspath(exe))
        candidates.append(os.path.join(exe_dir, 'ESDEngine.exe.WebView2'))

    local_appdata = os.environ.get('LOCALAPPDATA', '')
    if local_appdata:
        candidates.append(os.path.join(local_appdata, 'ESDEngine.exe.WebView2'))
        candidates.append(os.path.join(local_appdata, 'ESDEngine'))

    for path in candidates:
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
                print(f"[Dev] Cleared WebView2 cache: {path}")
            except Exception as e:
                print(f"[Dev] Warning: could not clear cache at {path}: {e}")

def launch_exe():
    exe = get_exe_path()
    if not exe:
        print("[Dev] Could not find compiled executable.")
        return None
    free_port()
    clear_webview_cache()
    print(f"[Dev] Starting {exe}...")
    environment = os.environ.copy()
    environment["EDK_WEB_ROOT"] = os.path.abspath(os.path.join(".edk", "desktop"))
    return subprocess.Popen([exe], env=environment)

def start_app(fresh=False):
    if fresh:
        clean_build()
    if not build_project():
        print("[Dev] Build failed. Waiting for changes to try again...")
        return None
    return launch_exe()


def validate_with_docker_if_configured():
    """Run disposable tests only when setup created the optional Docker definition."""
    dockerfile = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Dockerfile.edk")
    if not os.path.isfile(dockerfile):
        print("[Dev] Docker validation is not enabled; continuing with the local build.")
        return True
    return docker.main() == 0

def ask_startup_choice():
    print("\n" + "=" * 50)
    print("  EDK Desktop Development")
    print("=" * 50)
    print("\n  [1] Fresh build   — validates in a new container, then compiles from scratch")
    print("  [2] Previous build — launches the last compiled binary immediately")
    print()
    while True:
        choice = input("Select (1/2): ").strip()
        if choice in ('1', '2'):
            return choice
        print("  Please enter 1 or 2.")


def main():
    choice = ask_startup_choice()
    print(f"\n[Dev] Watching: {', '.join(WATCH_PATHS)}")

    if choice == '2':
        exe = get_exe_path()
        if exe:
            print(f"[Dev] Launching existing binary: {exe}")
            app_process = subprocess.Popen([exe])
        else:
            print("[Dev] No previous build found — running a fresh build instead.")
            if not validate_with_docker_if_configured():
                print("[Dev] Docker container setup failed; the fresh build was cancelled.")
                return 1
            app_process = start_app(fresh=True)
    else:
        if not validate_with_docker_if_configured():
            print("[Dev] Docker container setup failed; the fresh build was cancelled.")
            return 1
        app_process = start_app(fresh=True)

    last_mtime = get_latest_mtime()

    try:
        while True:
            time.sleep(1)
            current_mtime = get_latest_mtime()

            if current_mtime > last_mtime:
                print("\n[Dev] File changes detected — rebuilding...")

                if app_process and app_process.poll() is None:
                    app_process.terminate()
                    app_process.wait()

                app_process = start_app(fresh=False)
                last_mtime = get_latest_mtime()

    except KeyboardInterrupt:
        print("\n[Dev] Shutting down.")
        if app_process and app_process.poll() is None:
            app_process.terminate()
            app_process.wait()
        return 0

    return 0

def get_main_page():
    try:
        with open('properties.config', 'r', encoding='utf-8') as config:
            for line in config:
                if line.strip().startswith('MAIN_PAGE='):
                    value = line.split('=', 1)[1].strip().replace('\\', '/').lstrip('/')
                    if value:
                        return value
    except OSError:
        pass
    return 'ui/pages/index.html'


def install_live_reload():
    script = """<script>
(() => {
  let revision;
  setInterval(async () => {
    try {
      const next = await fetch('/__edk_revision', {cache: 'no-store'}).then(r => r.text());
      if (revision !== undefined && next !== revision) location.reload();
      revision = next;
    } catch (_) {}
  }, 500);
})();
</script>"""
    for html_file in Path(WEB_DEV_DIR).rglob('*.html'):
        document = html_file.read_text(encoding='utf-8')
        if '/__edk_revision' not in document:
            marker = '</body>'
            document = document.replace(marker, script + marker) if marker in document else document + script
            html_file.write_text(document, encoding='utf-8')


def compile_web_test():
    try:
        compile_frontend('web', optimize=False, output=Path(WEB_DEV_DIR), quiet=True)
        install_live_reload()
        WEB_REVISION['value'] += 1
        return True
    except Exception as error:
        print(f"[Dev] Web build failed: {error}")
        return False


class WebDevHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.abspath(WEB_DEV_DIR), **kwargs)

    def log_message(self, _format, *_args):
        pass

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        requested_url = urlsplit(self.path)
        if requested_url.path == '/__edk_revision':
            payload = str(WEB_REVISION['value']).encode('ascii')
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        requested = os.path.join(
            os.path.abspath(WEB_DEV_DIR),
            unquote(requested_url.path).lstrip('/').replace('/', os.sep)
        )
        accepts_html = 'text/html' in self.headers.get('Accept', '')
        if requested_url.path == '/' or (accepts_html and (
            not os.path.exists(requested) or os.path.isdir(requested)
        )):
            self.path = '/' + get_main_page()
        super().do_GET()


def start_web_server():
    preferred_port = get_server_port()
    try:
        server = ThreadingHTTPServer(('127.0.0.1', preferred_port), WebDevHandler)
    except OSError:
        server = ThreadingHTTPServer(('127.0.0.1', 0), WebDevHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def run_web_test():
    if not compile_web_test():
        return 1

    server = start_web_server()
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/{get_main_page()}"
    print(f"\n[Dev] Web test: {url}")
    print(f"[Dev] Watching: {', '.join(WATCH_PATHS)}")
    webbrowser.open(url)
    last_mtime = get_latest_mtime()

    try:
        while True:
            time.sleep(1)
            current_mtime = get_latest_mtime()
            if current_mtime > last_mtime:
                print("\n[Dev] Changes detected - rebuilding the web view...")
                compile_web_test()
                last_mtime = get_latest_mtime()
    except KeyboardInterrupt:
        print("\n[Dev] Shutting down web test.")
    finally:
        server.shutdown()
        server.server_close()
    return 0


def run_desktop_test():
    print(f"\n[Dev] Watching: {', '.join(WATCH_PATHS)}")
    fresh = get_exe_path() is None
    if fresh and not validate_with_docker_if_configured():
        print("[Dev] Docker validation failed; the desktop build was cancelled.")
        return 1

    app_process = start_app(fresh=fresh)
    last_mtime = get_latest_mtime()

    try:
        while True:
            time.sleep(1)
            current_mtime = get_latest_mtime()
            if current_mtime > last_mtime:
                print("\n[Dev] File changes detected - rebuilding desktop app...")
                if app_process and app_process.poll() is None:
                    app_process.terminate()
                    app_process.wait()
                app_process = start_app(fresh=False)
                last_mtime = get_latest_mtime()
    except KeyboardInterrupt:
        print("\n[Dev] Shutting down desktop test.")
        if app_process and app_process.poll() is None:
            app_process.terminate()
            app_process.wait()
    return 0


def ask_test_target():
    print("\n" + "=" * 50)
    print("  EDK Development")
    print("=" * 50)
    print("\n  [1] Web test     - opens the app in your default browser")
    print("  [2] Desktop test - builds and opens the native desktop app")
    print()
    while True:
        choice = input("Select (1/2): ").strip()
        if choice in ('1', '2'):
            return choice
        print("  Please enter 1 or 2.")


def development_main():
    choice = ask_test_target()
    return run_web_test() if choice == '1' else run_desktop_test()

if __name__ == '__main__':
    sys.exit(development_main())
