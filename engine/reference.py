"""Generate a Markdown reference from project JSDoc blocks."""
from __future__ import annotations
import argparse, re
from pathlib import Path
PROJECT_DIR = Path(__file__).resolve().parent.parent

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT_DIR / "reference" / "README.md")
    arguments = parser.parse_args(); sections = ["# EWDK Project Reference\n"]
    for folder in ("scripts", "functions", "classes", "modules"):
        root = PROJECT_DIR / folder
        if not root.is_dir(): continue
        for source in sorted(path for path in root.rglob("*") if path.suffix in {".ts", ".js", ".mjs"}):
            blocks = re.findall(r"/\*\*(.*?)\*/", source.read_text(encoding="utf-8"), re.DOTALL)
            if blocks:
                sections.append(f"## `{source.relative_to(PROJECT_DIR).as_posix()}`\n")
                for block in blocks:
                    sections.append("\n".join(re.sub(r"^\s*\* ?", "", line).rstrip() for line in block.splitlines()).strip() + "\n")
    if len(sections) == 1: sections.append("No JSDoc blocks were found.\n")
    output = arguments.output if arguments.output.is_absolute() else PROJECT_DIR / arguments.output
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text("\n".join(sections), encoding="utf-8")
    print(f"EWDK: generated {output}"); return 0
if __name__ == "__main__": raise SystemExit(main())
