"""Build an EWDK source tree into browser-ready files in ``dist``."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ENGINE_DIR.parent
SOURCE_DIRS = ("pages", "components", "scripts", "functions", "classes", "modules")


def _tailwind_enabled() -> bool:
    requirements = PROJECT_DIR / "requirements.txt"
    if not requirements.exists():
        return False
    for raw in requirements.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and line.partition("=")[0].strip().lower() in {
            "tailwind", "tailwindcss", "@tailwindcss/cli"
        }:
            return True
    return False


def _run(command: list[str], *, cwd: Path = PROJECT_DIR, quiet: bool = False) -> None:
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if quiet and hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        subprocess.run(
            command, cwd=cwd, check=True, capture_output=quiet, text=quiet, creationflags=creationflags
        )
    except FileNotFoundError as error:
        raise RuntimeError(f"Required program '{command[0]}' was not found") from error
    except subprocess.CalledProcessError as error:
        details = f": {(error.stderr or error.stdout).strip()}" if quiet and (error.stderr or error.stdout) else ""
        raise RuntimeError(f"Command failed with exit code {error.returncode}: {' '.join(command)}{details}") from error


def _npx(*arguments: str, cwd: Path = PROJECT_DIR, quiet: bool = False) -> None:
    executable = "npx.cmd" if shutil.which("npx.cmd") else "npx"
    _run([executable, "--no-install", *arguments], cwd=cwd, quiet=quiet)


def _terser(source: str) -> str:
    executable = "npx.cmd" if shutil.which("npx.cmd") else "npx"
    try:
        result = subprocess.run(
            [executable, "--no-install", "terser", "--compress", "passes=2", "--mangle", "toplevel"],
            cwd=PROJECT_DIR,
            input=source,
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"Terser failed: {error.stderr.strip()}") from error


def _minify_css(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    source = re.sub(r"\s+", " ", source)
    source = re.sub(r"\s*([{}:;,>])\s*", r"\1", source)
    return source.strip().replace(";}", "}")


def _extract_blocks(source: str, tag: str) -> tuple[list[tuple[str, str]], str]:
    pattern = re.compile(rf"<{tag}\b([^>]*)>(.*?)</{tag}\s*>", re.IGNORECASE | re.DOTALL)
    blocks = [(match.group(1).strip(), match.group(2)) for match in pattern.finditer(source)]
    return blocks, pattern.sub("", source)


def _compile_typescript(staging: Path, quiet: bool = False) -> None:
    inputs = [
        path
        for folder in ("scripts", "functions", "classes")
        if (PROJECT_DIR / folder).is_dir()
        for path in (PROJECT_DIR / folder).rglob("*.ts")
    ]
    if not inputs:
        return

    command = [
        "tsc",
        "--target", "ES2020",
        "--module", "ES2020",
        "--moduleResolution", "bundler",
        "--allowJs", "true",
        "--checkJs", "false",
        "--rootDir", str(PROJECT_DIR),
        "--outDir", str(staging),
        "--sourceMap", "false",
        "--declaration", "false",
        *map(str, inputs),
    ]
    _npx(*command, quiet=quiet)


def _obfuscate_javascript(staging: Path) -> None:
    javascript = sorted(staging.rglob("*.js")) + sorted(staging.rglob("*.mjs"))
    if not javascript:
        return

    for source in javascript:
        source.write_text(_terser(source.read_text(encoding="utf-8")), encoding="utf-8")


def _minify_javascript_text(source: str) -> str:
    if not source.strip():
        return source.strip()
    return _terser(source)


def _page_document(source: str, page: Path, optimize: bool, tailwind_href: str | None = None) -> str:
    styles, remainder = _extract_blocks(source, "style")
    scripts, remainder = _extract_blocks(remainder, "script")
    templates, remainder = _extract_blocks(remainder, "template")
    body = "\n".join(content.strip() for _, content in templates).strip()
    if not body:
        body = remainder.strip()

    style_html = "" if tailwind_href else "".join(f"<style>{_minify_css(content)}</style>" for _, content in styles)
    stylesheet = f'<link rel="stylesheet" href="{html.escape(tailwind_href)}">' if tailwind_href else ""
    script_html = "".join(
        f"<script{(' ' + attributes) if attributes else ''}>"
        f"{_minify_javascript_text(content) if optimize else content.strip()}</script>"
        for attributes, content in scripts
    )
    title = html.escape(page.stem.replace("-", " ").replace("_", " ").title())
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{title}</title>{stylesheet}{style_html}</head><body>{body}{script_html}</body></html>\n"
    )


def _copy_sources(staging: Path, tailwind: bool) -> None:
    for folder_name in SOURCE_DIRS:
        source = PROJECT_DIR / folder_name
        target = staging / folder_name
        if not source.is_dir():
            continue
        destination = staging if folder_name == "pages" else target
        shutil.copytree(
            source,
            destination,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(
                "*.ts", "*.css" if tailwind else "__never_css__",
                "*.html" if folder_name == "pages" else "__never_html__", "__pycache__", "*.pyc"
            ),
        )


def _compile_tailwind(staging: Path, optimize: bool, quiet: bool = False) -> None:
    parts = ['@import "tailwindcss";']
    for folder in SOURCE_DIRS:
        if (PROJECT_DIR / folder).is_dir():
            parts.append(f'@source "../{folder}";')

    for folder in SOURCE_DIRS:
        root = PROJECT_DIR / folder
        if not root.is_dir():
            continue
        for stylesheet in sorted(root.rglob("*.css")):
            parts.append(stylesheet.read_text(encoding="utf-8"))
        for document in sorted(root.rglob("*.html")):
            styles, _ = _extract_blocks(document.read_text(encoding="utf-8"), "style")
            parts.extend(content for _, content in styles)

    input_file = staging / ".tailwind-input.css"
    output_file = staging / "ewdk.css"
    input_file.write_text("\n".join(parts), encoding="utf-8")
    arguments = ["tailwindcss", "-i", str(input_file), "-o", str(output_file)]
    if optimize:
        arguments.append("--minify")
    try:
        _npx(*arguments, quiet=quiet)
    except RuntimeError as error:
        raise RuntimeError("Tailwind is listed in requirements.txt but is not installed; run python engine/install.py") from error
    finally:
        input_file.unlink(missing_ok=True)


def build(*, clean: bool = True, optimize: bool = True, quiet: bool = False) -> Path:
    output = PROJECT_DIR / "dist"
    staging = Path(tempfile.mkdtemp(prefix=".ewdk-build-", dir=PROJECT_DIR))
    tailwind = _tailwind_enabled()

    try:
        _copy_sources(staging, tailwind)
        _compile_typescript(staging, quiet)

        pages = PROJECT_DIR / "pages"
        if pages.is_dir():
            for page in pages.rglob("*.html"):
                relative = page.relative_to(pages)
                target = staging / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                tailwind_href = "../" * len(relative.parent.parts) + "ewdk.css" if tailwind else None
                target.write_text(
                    _page_document(page.read_text(encoding="utf-8"), page, optimize, tailwind_href), encoding="utf-8"
                )

        if tailwind:
            _compile_tailwind(staging, optimize, quiet)

        for stylesheet in staging.rglob("*.css"):
            stylesheet.write_text(_minify_css(stylesheet.read_text(encoding="utf-8")), encoding="utf-8")
        if optimize:
            _obfuscate_javascript(staging)

        manifest = {
            "generator": "EWDK",
            "entry": "index.html",
            "optimized": optimize,
            "tailwind": tailwind,
        }
        (staging / "ewdk-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        if clean and output.exists():
            shutil.rmtree(output)
        output.mkdir(exist_ok=True)
        shutil.copytree(staging, output, dirs_exist_ok=True)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    if not quiet:
        print(f"EWDK: built {output}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-clean", action="store_true", help="Keep files already present in dist")
    parser.add_argument("--no-optimize", action="store_true", help="Skip JavaScript minification/mangling")
    arguments = parser.parse_args()
    try:
        build(clean=not arguments.no_clean, optimize=not arguments.no_optimize)
        return 0
    except RuntimeError as error:
        print(f"EWDK build error: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
