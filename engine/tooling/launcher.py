"""Dependency bootstrap used by EDK's public Windows batch commands."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from engine.tooling.requirements import read_requirements, write_pip_requirements, has_installable_requirements
except ImportError:
    from requirements import read_requirements, write_pip_requirements, has_installable_requirements


PROJECT_DIR = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_DIR / ".edk"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "none"


def run(command: list[str], *, quiet: bool = False) -> None:
    executable = command[0]
    if executable in {"npm", "npx"} and shutil.which(executable + ".cmd"):
        command[0] += ".cmd"
    options = {}
    if os.name == "nt":
        options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.run(
        command,
        cwd=PROJECT_DIR,
        check=True,
        stdin=None,
        stdout=subprocess.DEVNULL if quiet else None,
        stderr=subprocess.DEVNULL if quiet else None,
        **options,
    )


def sync_python_dependencies() -> None:
    requirements = PROJECT_DIR / "requirements.txt"
    digest = file_hash(requirements)
    stamp = STATE_DIR / "requirements.sha256"
    if stamp.exists() and stamp.read_text(encoding="utf-8").strip() == digest:
        return
    _, pip_lines = read_requirements(str(requirements))
    if has_installable_requirements(pip_lines):
        print("  > Installing Python dependencies...")
        temporary = write_pip_requirements(pip_lines)
        try:
            run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-r", temporary])
        finally:
            Path(temporary).unlink(missing_ok=True)
    stamp.write_text(digest, encoding="utf-8")


def find_npm() -> str | None:
    return shutil.which("npm.cmd") or shutil.which("npm")


def ensure_node() -> str:
    npm = find_npm()
    if npm:
        return npm
    winget = shutil.which("winget")
    if not winget:
        raise RuntimeError("Windows Package Manager is required to install Node.js automatically.")
    print("  > Installing the frontend compiler runtime...")
    run([
        winget, "install", "--id", "OpenJS.NodeJS.LTS", "--exact", "--silent",
        "--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity",
    ])
    os.environ["PATH"] = os.pathsep.join(filter(None, [
        os.environ.get("PATH"),
        os.environ.get("ProgramFiles", "") + r"\nodejs",
    ]))
    npm = find_npm()
    if not npm:
        raise RuntimeError("Node.js was installed. Open a new terminal, then run the command again.")
    return npm


def sync_frontend_dependencies() -> None:
    package = PROJECT_DIR / "package.json"
    if not package.exists():
        return
    digest = file_hash(package)
    stamp = STATE_DIR / "frontend.sha256"
    if (PROJECT_DIR / "node_modules").exists() and stamp.exists() and stamp.read_text(encoding="utf-8").strip() == digest:
        return
    npm = ensure_node()
    print("  > Installing frontend dependencies...")
    run([npm, "install", "--no-audit", "--no-fund"])
    stamp.write_text(digest, encoding="utf-8")


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: launcher.py <setup|dev|build|docker|package|update> [arguments]")
        return 2
    tool, *arguments = sys.argv[1:]
    if tool not in {"setup", "dev", "build", "docker", "package", "update"}:
        print(f"Unknown EDK command: {tool}")
        return 2
    STATE_DIR.mkdir(exist_ok=True)
    sync_python_dependencies()
    sync_frontend_dependencies()
    script = PROJECT_DIR / "engine" / "tooling" / f"{tool}.py"
    if not script.exists():
        raise RuntimeError(f"Internal EDK tool is missing: {script}")
    return subprocess.call([sys.executable, str(script), *arguments], cwd=PROJECT_DIR)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as error:
        print(f"  !! {error}")
        raise SystemExit(1)
