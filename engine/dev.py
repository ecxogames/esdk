"""Build on changes and serve the EWDK project from ``dist``."""

from __future__ import annotations

import argparse
import hashlib
import http.server
import threading
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

from build import PROJECT_DIR, SOURCE_DIRS, build

LIVE_RELOAD = """<script>(()=>{let v;setInterval(async()=>{try{const n=await fetch('/__ewdk_version',{cache:'no-store'}).then(r=>r.text());if(v&&n!==v)location.reload();v=n}catch{}},500)})()</script>"""


def _inject_live_reload(output: Path) -> None:
    for page in output.rglob("*.html"):
        source = page.read_text(encoding="utf-8")
        source = source.replace("</body>", f"{LIVE_RELOAD}</body>") if "</body>" in source else source + LIVE_RELOAD
        page.write_text(source, encoding="utf-8")


def _fingerprint() -> str:
    digest = hashlib.sha256()
    watched = [PROJECT_DIR / "properties.config", PROJECT_DIR / "requirements.txt"]
    for folder in SOURCE_DIRS:
        root = PROJECT_DIR / folder
        if root.is_dir():
            watched.extend(path for path in root.rglob("*") if path.is_file())
    for path in sorted(watched):
        if path.is_file():
            try:
                digest.update(str(path.relative_to(PROJECT_DIR)).encode())
                digest.update(path.read_bytes())
            except OSError:
                # Editors may briefly replace a file while saving. The next
                # watcher pass will hash the completed replacement.
                continue
    return digest.hexdigest()


def _watch(
    stop: threading.Event, interval: float, output: Path, version: dict[str, str], verbose: bool
) -> None:
    previous = _fingerprint()
    while not stop.wait(interval):
        current = _fingerprint()
        if current == previous:
            continue
        try:
            build(optimize=False, quiet=not verbose)
            _inject_live_reload(output)
            previous = current
            version["value"] = current
            print("EWDK: changes rebuilt; connected browsers reloading", flush=True)
        except Exception as error:  # Keep the dev server alive after a bad edit.
            print(f"EWDK rebuild error: {error}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--no-open", action="store_true", help="Do not open the browser")
    parser.add_argument("--interval", type=float, default=0.5, help="Watch interval in seconds")
    parser.add_argument("--verbose", action="store_true", help="Show compiler and HTTP request logs")
    arguments = parser.parse_args()

    try:
        output = build(optimize=False, quiet=not arguments.verbose)
    except Exception as error:
        if arguments.verbose:
            raise
        print(f"EWDK startup error: {error}")
        return 1
    _inject_live_reload(output)
    version = {"value": _fingerprint()}

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *handler_args, **handler_kwargs):
            super().__init__(*handler_args, directory=str(output), **handler_kwargs)

        def end_headers(self) -> None:
            # Development assets keep stable URLs, so disable browser and
            # intermediary caches to ensure rebuilt HTML/CSS/JS is fetched.
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            super().end_headers()

        def log_message(self, format: str, *message_args) -> None:
            if arguments.verbose:
                super().log_message(format, *message_args)

        def do_GET(self) -> None:
            if urlparse(self.path).path == "/__ewdk_version":
                payload = version["value"].encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            super().do_GET()

    handler = Handler
    server = http.server.ThreadingHTTPServer((arguments.host, arguments.port), handler)
    stop = threading.Event()
    watcher = threading.Thread(
        target=_watch, args=(stop, arguments.interval, output, version, arguments.verbose), daemon=True
    )
    watcher.start()
    url = f"http://{arguments.host}:{server.server_port}/"
    print(f"EWDK: serving {output} at {url} (Ctrl+C to stop)")
    if not arguments.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEWDK: development server stopped")
    finally:
        stop.set()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
