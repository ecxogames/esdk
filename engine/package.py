"""Build the website and package ``dist`` as a zip archive."""
from __future__ import annotations
import argparse, shutil
from build import PROJECT_DIR, build

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default=PROJECT_DIR.name, help="Archive name without .zip")
    arguments = parser.parse_args()
    try:
        output = build()
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in arguments.name)
        result = shutil.make_archive(str(PROJECT_DIR / safe), "zip", root_dir=output)
        print(f"EWDK: packaged {result}"); return 0
    except (OSError, RuntimeError) as error: print(f"EWDK package error: {error}"); return 1
if __name__ == "__main__": raise SystemExit(main())
