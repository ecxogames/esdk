"""Install EWDK's Node-based compiler dependencies."""
from __future__ import annotations
import argparse, json, shutil, subprocess
from pathlib import Path
PROJECT_DIR = Path(__file__).resolve().parent.parent

def _npm(*arguments: str) -> None:
    executable = "npm.cmd" if shutil.which("npm.cmd") else "npm"
    try: subprocess.run([executable, *arguments], cwd=PROJECT_DIR, check=True)
    except FileNotFoundError as error: raise RuntimeError("Node.js/npm is required but was not found") from error
    except subprocess.CalledProcessError as error: raise RuntimeError(f"npm failed with exit code {error.returncode}") from error

def _requirements() -> list[str]:
    packages = []
    tailwind_version = ""
    for raw in (PROJECT_DIR / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"): continue
        name, separator, version = line.partition("=")
        normalized = name.strip().lower()
        if normalized in {"tailwind", "tailwindcss", "@tailwindcss/cli"}:
            if separator and version: tailwind_version = version.strip()
            continue
        packages.append(f"{name.strip()}@{version.strip()}" if separator and version else name.strip())
    if tailwind_version or any(
        raw.strip().partition("=")[0].lower() in {"tailwind", "tailwindcss", "@tailwindcss/cli"}
        for raw in (PROJECT_DIR / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if raw.strip() and not raw.strip().startswith("#")
    ):
        suffix = f"@{tailwind_version}" if tailwind_version else ""
        packages.extend((f"tailwindcss{suffix}", f"@tailwindcss/cli{suffix}"))
    return packages

def Install() -> None:
    package_file = PROJECT_DIR / "package.json"
    if not package_file.exists(): package_file.write_text(json.dumps({"name": "ewdk-app", "private": True}, indent=2) + "\n", encoding="utf-8")
    packages = _requirements()
    if packages: _npm("install", "--save-dev", *packages)

def Tailwind() -> None: _npm("install", "--save-dev", "tailwindcss", "@tailwindcss/cli")
def Typescript() -> None: _npm("install", "--save-dev", "typescript")

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dependency", nargs="?", choices=("all", "tailwind", "typescript"), default="all")
    arguments = parser.parse_args()
    try: {"all": Install, "tailwind": Tailwind, "typescript": Typescript}[arguments.dependency](); return 0
    except RuntimeError as error: print(f"EWDK install error: {error}"); return 1
if __name__ == "__main__": raise SystemExit(main())
