import base64
import glob
import mimetypes
import os
import re
import sys

BASE_DELIM = "ESD_HTML_END"
MAX_LITERAL_BYTES = 12_000


def _local_asset_path(html_path, reference):
    if not reference or reference.startswith(("http://", "https://", "data:", "//", "#")):
        return None
    clean_reference = reference.split("?", 1)[0].split("#", 1)[0]
    asset_path = os.path.normpath(os.path.join(os.path.dirname(html_path), clean_reference))
    return asset_path if os.path.isfile(asset_path) else None


def _inline_local_assets(html_path, content):
    def replace_stylesheet(match):
        tag, reference = match.group(0), match.group("reference")
        if not re.search(r"\brel\s*=\s*(['\"])stylesheet\1", tag, re.IGNORECASE):
            return tag
        asset_path = _local_asset_path(html_path, reference)
        if not asset_path:
            return tag
        with open(asset_path, "r", encoding="utf-8") as asset_file:
            css = re.sub(r"</style", r"<\\/style", asset_file.read(), flags=re.IGNORECASE)
        return f'<style data-esd-source="{reference}">\n{css}\n</style>'

    def replace_script(match):
        reference = match.group("reference")
        asset_path = _local_asset_path(html_path, reference)
        if not asset_path:
            return match.group(0)
        with open(asset_path, "r", encoding="utf-8") as asset_file:
            javascript = re.sub(r"</script", r"<\\/script", asset_file.read(), flags=re.IGNORECASE)
        return f'<script data-esd-source="{reference}">\n{javascript}\n</script>'

    def replace_binary_source(match):
        reference = match.group("reference")
        asset_path = _local_asset_path(html_path, reference)
        if not asset_path:
            return match.group(0)
        mime_type = mimetypes.guess_type(asset_path)[0] or "application/octet-stream"
        with open(asset_path, "rb") as asset_file:
            encoded = base64.b64encode(asset_file.read()).decode("ascii")
        return match.group(0).replace(reference, f"data:{mime_type};base64,{encoded}", 1)

    content = re.sub(
        r"<link\b[^>]*?\bhref\s*=\s*(?P<quote>['\"])(?P<reference>.*?)(?P=quote)[^>]*>",
        replace_stylesheet, content, flags=re.IGNORECASE,
    )
    content = re.sub(
        r"<script\b[^>]*?\bsrc\s*=\s*(?P<quote>['\"])(?P<reference>.*?)(?P=quote)[^>]*>\s*</script\s*>",
        replace_script, content, flags=re.IGNORECASE,
    )
    return re.sub(
        r"<(?:img|source)\b[^>]*?\bsrc\s*=\s*(?P<quote>['\"])(?P<reference>.*?)(?P=quote)[^>]*>",
        replace_binary_source, content, flags=re.IGNORECASE,
    )


def _content_chunks(content, max_bytes=MAX_LITERAL_BYTES):
    """Split text without splitting UTF-8 characters or exceeding MSVC's literal limit."""
    chunks, current, current_bytes = [], [], 0
    for character in content:
        character_bytes = len(character.encode("utf-8"))
        if current and current_bytes + character_bytes > max_bytes:
            chunks.append("".join(current))
            current, current_bytes = [], 0
        current.append(character)
        current_bytes += character_bytes
    if current or not chunks:
        chunks.append("".join(current))
    return chunks


def embed_html(output_path, ui_root="ui"):
    seen, unique_files = set(), []
    ui_root = os.path.abspath(ui_root)
    for pattern in [os.path.join(ui_root, "**", "*.html"), os.path.join(ui_root, "*.html")]:
        for filepath in glob.glob(pattern, recursive=True):
            key = "ui/" + os.path.relpath(filepath, ui_root).replace("\\", "/")
            if key not in seen:
                seen.add(key)
                unique_files.append((key, filepath))

    lines = [
        "#pragma once", "#include <initializer_list>", "#include <string>",
        "#include <string_view>", "#include <unordered_map>", "",
        "inline std::string JoinEmbeddedHtml(std::initializer_list<std::string_view> chunks) {",
        "    std::size_t total = 0;", "    for (const auto chunk : chunks) total += chunk.size();",
        "    std::string result;", "    result.reserve(total);",
        "    for (const auto chunk : chunks) result.append(chunk.data(), chunk.size());",
        "    return result;", "}", "",
        "inline const std::unordered_map<std::string, std::string>& GetEmbeddedHtml() {",
        "    static const std::unordered_map<std::string, std::string> map = {",
    ]

    for key, filepath in unique_files:
        with open(filepath, "r", encoding="utf-8") as file:
            content = _inline_local_assets(filepath, file.read())
        delim, counter = BASE_DELIM, 0
        while f"){delim}\"" in content:
            counter += 1
            delim = f"{BASE_DELIM}_{counter}"
        literals = ",\n".join(
            f'            R"{delim}({chunk}){delim}"' for chunk in _content_chunks(content)
        )
        lines.append(f'        {{"{key}", JoinEmbeddedHtml({{\n{literals}\n        }})}},')
        print(f"[embed_html] Embedded: {key}")

    lines += ["    };", "    return map;", "}"]
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")
    print(f"[embed_html] Generated '{output_path}' with {len(unique_files)} HTML file(s).")


if __name__ == "__main__":
    embed_html(
        sys.argv[1] if len(sys.argv) > 1 else "engine/embedded_html.h",
        sys.argv[2] if len(sys.argv) > 2 else "ui",
    )
