"""Compile EDK's shared ui/ source tree for desktop or web targets."""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import time
from html.parser import HTMLParser
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
UI_DIR = PROJECT_DIR / "ui"
FRONTEND_DIRS = ("pages", "components", "scripts", "functions", "classes", "modules", "styles", "themes")


def _remove_tree(path: Path):
    if not path.exists():
        return
    def retry(function, target, _error):
        Path(target).chmod(Path(target).stat().st_mode | stat.S_IWRITE)
        function(target)
    last_error = None
    for attempt in range(5):
        try:
            shutil.rmtree(path, onerror=retry)
            return
        except (OSError, PermissionError) as error:
            last_error = error
            time.sleep(0.35 * (attempt + 1))
    raise RuntimeError(f"Could not replace frontend output '{path}': {last_error}")


class _TargetFilter(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, target: str):
        super().__init__(convert_charrefs=False)
        self.target = target
        self.output: list[str] = []
        self.skipped_depth = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        declared = values.get("target", "").lower()
        platform_target = declared if declared in {"desktop", "web"} else ""
        if self.skipped_depth:
            if tag not in self.VOID:
                self.skipped_depth += 1
            return
        if platform_target and platform_target != self.target:
            if tag not in self.VOID:
                self.skipped_depth = 1
            return
        rendered = []
        for name, value in attrs:
            if name.lower() == "target" and platform_target:
                continue
            rendered.append(name if value is None else f'{name}="{html.escape(value, quote=True)}"')
        self.output.append(f"<{tag}{(' ' + ' '.join(rendered)) if rendered else ''}>")

    def handle_startendtag(self, tag, attrs):
        values = dict(attrs)
        declared = values.get("target", "").lower()
        if declared in {"desktop", "web"} and declared != self.target:
            return
        rendered = [
            name if value is None else f'{name}="{html.escape(value, quote=True)}"'
            for name, value in attrs if not (name.lower() == "target" and declared in {"desktop", "web"})
        ]
        self.output.append(f"<{tag}{(' ' + ' '.join(rendered)) if rendered else ''}/>")

    def handle_endtag(self, tag):
        if self.skipped_depth:
            self.skipped_depth -= 1
        else:
            self.output.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.skipped_depth:
            self.output.append(data)

    def handle_entityref(self, name):
        if not self.skipped_depth:
            self.output.append(f"&{name};")

    def handle_charref(self, name):
        if not self.skipped_depth:
            self.output.append(f"&#{name};")

    def handle_comment(self, data):
        if not self.skipped_depth:
            self.output.append(f"<!--{data}-->")

    def handle_decl(self, decl):
        if not self.skipped_depth:
            self.output.append(f"<!{decl}>")

    def handle_pi(self, data):
        if not self.skipped_depth:
            self.output.append(f"<?{data}>")


def filter_target_html(source: str, target: str) -> str:
    parser = _TargetFilter(target)
    parser.feed(source)
    parser.close()
    return "".join(parser.output)


def _run(command: list[str], *, quiet=False, input_text=None) -> subprocess.CompletedProcess:
    executable = command[0]
    if executable in {"npm", "npx"} and shutil.which(executable + ".cmd"):
        command[0] += ".cmd"
    try:
        return subprocess.run(
            command, cwd=PROJECT_DIR, check=True, text=True, input=input_text,
            capture_output=quiet or input_text is not None,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError as error:
        raise RuntimeError(f"Required program '{executable}' was not found; run .\\scripts\\setup.ps1") from error
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "").strip()
        raise RuntimeError(f"{' '.join(command)} failed{': ' + detail if detail else ''}") from error


def _npx(*arguments: str, quiet=False):
    return _run(["npx", "--no-install", *arguments], quiet=quiet)


def _node_dependencies_ready() -> bool:
    return (PROJECT_DIR / "node_modules" / "typescript").exists() and (PROJECT_DIR / "node_modules" / "terser").exists()


def ensure_frontend_dependencies(quiet=False):
    if not (PROJECT_DIR / "package.json").exists():
        return
    if not _node_dependencies_ready():
        _run(["npm", "install", "--no-audit", "--no-fund"], quiet=quiet)


def _tailwind_enabled() -> bool:
    package_file = PROJECT_DIR / "package.json"
    if package_file.exists():
        try:
            package = json.loads(package_file.read_text(encoding="utf-8"))
            dependencies = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
            if "tailwindcss" in dependencies or "@tailwindcss/cli" in dependencies:
                return True
        except (OSError, json.JSONDecodeError):
            pass
    requirements = PROJECT_DIR / "requirements.txt"
    if not requirements.exists():
        return False
    return any(
        line.strip().lower().split("=", 1)[0].strip() in {"tailwind", "tailwindcss", "@tailwindcss/cli"}
        for line in requirements.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def _terser(source: str) -> str:
    if not source.strip():
        return ""
    return _run(
        ["npx", "--no-install", "terser", "--compress", "passes=2", "--mangle", "toplevel"],
        quiet=True, input_text=source,
    ).stdout.strip()


def _minify_css(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    source = re.sub(r"\s+", " ", source)
    return re.sub(r"\s*([{}:;,>])\s*", r"\1", source).strip().replace(";}", "}")


def _compile_typescript(ui_staging: Path, quiet=False):
    inputs = [path for folder in FRONTEND_DIRS if (UI_DIR / folder).is_dir() for path in (UI_DIR / folder).rglob("*.ts")]
    if not inputs:
        return
    _npx(
        "tsc", "--target", "ES2020", "--module", "ES2020", "--moduleResolution", "bundler",
        "--allowJs", "true", "--checkJs", "false", "--rootDir", str(UI_DIR),
        "--outDir", str(ui_staging), "--sourceMap", "false", "--declaration", "false",
        *map(str, inputs), quiet=quiet,
    )


def _compile_tailwind(ui_staging: Path, optimize: bool, quiet=False):
    parts = ['@import "tailwindcss";']
    for folder in FRONTEND_DIRS:
        if (UI_DIR / folder).is_dir():
            parts.append(f'@source "../../ui/{folder}";')
    for stylesheet in UI_DIR.rglob("*.css"):
        parts.append(stylesheet.read_text(encoding="utf-8"))
    source = ui_staging / ".tailwind-input.css"
    output = ui_staging / "edk.css"
    source.write_text("\n".join(parts), encoding="utf-8")
    args = ["tailwindcss", "-i", str(source), "-o", str(output)]
    if optimize:
        args.append("--minify")
    try:
        _npx(*args, quiet=quiet)
    finally:
        source.unlink(missing_ok=True)


def _copy_ui(ui_staging: Path, target: str, tailwind: bool):
    shutil.copytree(
        UI_DIR, ui_staging, dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("*.ts", "*.css" if tailwind else "__never__", "__pycache__", "*.pyc"),
    )
    for page in ui_staging.rglob("*.html"):
        page.write_text(filter_target_html(page.read_text(encoding="utf-8"), target), encoding="utf-8")


def compile_frontend(target="desktop", *, optimize=False, output: Path | None = None, quiet=False) -> Path:
    if target not in {"desktop", "web"}:
        raise ValueError("target must be 'desktop' or 'web'")
    ensure_frontend_dependencies(quiet=quiet)
    destination = output or PROJECT_DIR / ".edk" / target
    state_root = PROJECT_DIR / ".edk"
    state_root.mkdir(exist_ok=True)
    staging_root = Path(tempfile.mkdtemp(prefix="frontend-", dir=state_root))
    ui_staging = staging_root / "ui"
    tailwind = _tailwind_enabled()
    try:
        _copy_ui(ui_staging, target, tailwind)
        _compile_typescript(ui_staging, quiet=quiet)
        if tailwind:
            _compile_tailwind(ui_staging, optimize, quiet=quiet)
            for page in ui_staging.rglob("*.html"):
                text = page.read_text(encoding="utf-8")
                href = Path(os.path.relpath(ui_staging / "edk.css", page.parent)).as_posix()
                link = f'<link rel="stylesheet" href="{href}">'
                text = text.replace("</head>", link + "</head>") if "</head>" in text.lower() else link + text
                page.write_text(text, encoding="utf-8")
        if optimize:
            for script in list(ui_staging.rglob("*.js")) + list(ui_staging.rglob("*.mjs")):
                script.write_text(_terser(script.read_text(encoding="utf-8")), encoding="utf-8")
            for stylesheet in ui_staging.rglob("*.css"):
                stylesheet.write_text(_minify_css(stylesheet.read_text(encoding="utf-8")), encoding="utf-8")
        if destination.exists():
            _remove_tree(destination)
        shutil.copytree(staging_root, destination)
    finally:
        _remove_tree(staging_root)
    return destination


def publish_web(*, optimize=True, quiet=False) -> Path:
    output = PROJECT_DIR / "dist" / "Web"
    compiled = compile_frontend("web", optimize=optimize, output=output, quiet=quiet)
    config = {}
    config_file = PROJECT_DIR / "properties.config"
    if config_file.exists():
        for raw in config_file.read_text(encoding="utf-8").splitlines():
            if "=" in raw and not raw.lstrip().startswith("#"):
                key, value = raw.split("=", 1)
                config[key.strip()] = value.strip()
    main_page = config.get("MAIN_PAGE", "ui/pages/index.html").replace("\\", "/")
    entry = compiled / main_page
    if not entry.exists():
        raise RuntimeError(f"Web entry page was not found after compilation: {main_page}")
    entry_html = entry.read_text(encoding="utf-8")
    base = f'<base href="{Path(main_page).parent.as_posix()}/">'
    if "<head" in entry_html.lower():
        entry_html = re.sub(r"(<head\b[^>]*>)", r"\1" + base, entry_html, count=1, flags=re.IGNORECASE)
    else:
        entry_html = base + entry_html
    (compiled / "index.html").write_text(entry_html, encoding="utf-8")
    manifest = {"generator": "EDK", "entry": "index.html", "source": main_page,
                "optimized": optimize, "tailwind": _tailwind_enabled()}
    (compiled / "edk-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if not quiet:
        print(f"[EDK] Web site built at {compiled}")
    return compiled
