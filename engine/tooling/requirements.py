"""Helpers for ESDK's requirements.txt runtime directive and pip packages."""

import os
import re
import sys
import tempfile


PYTHON_DIRECTIVE = re.compile(r"^python\s*==\s*([0-9]+\.[0-9]+\.[0-9]+)$", re.IGNORECASE)


def read_requirements(path="requirements.txt"):
    python_version = None
    pip_lines = []

    if not os.path.exists(path):
        return python_version, pip_lines

    with open(path, "r", encoding="utf-8") as requirements_file:
        for raw_line in requirements_file:
            stripped = raw_line.strip()
            match = PYTHON_DIRECTIVE.match(stripped)
            if match:
                if python_version:
                    raise ValueError("requirements.txt contains more than one python== version directive")
                python_version = match.group(1)
            else:
                pip_lines.append(raw_line.rstrip("\n"))

    return python_version, pip_lines


def resolved_python_version(path="requirements.txt"):
    configured, _ = read_requirements(path)
    return configured or f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def ensure_compatible_interpreter(version):
    requested = tuple(int(part) for part in version.split(".")[:2])
    running = (sys.version_info.major, sys.version_info.minor)
    if requested != running:
        raise RuntimeError(
            f"requirements.txt requests Python {version}, but this build is running with "
            f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}. "
            f"Run the ESDK scripts with Python {requested[0]}.{requested[1]}."
        )


def write_pip_requirements(lines):
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix="-esdk-requirements.txt", delete=False, encoding="utf-8"
    )
    with handle:
        handle.write("\n".join(lines).strip() + "\n")
    return handle.name


def has_installable_requirements(lines):
    return any(line.strip() and not line.lstrip().startswith("#") for line in lines)
