# ESDK Documentation

ESDK builds Windows desktop apps with HTML, CSS, JavaScript, C++, and an embedded Python backend.

## Start here

1. Run `powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1` once.
2. Edit `ui/pages/index.html`.
3. Run `powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1`.

The PowerShell commands find or install the requested Python version and install the packages in `requirements.txt` for you.

## Guides

- [Backend](backend.md): call Python from JavaScript.
- [Public modules](public-modules.md): reusable, non-sensitive Python code.
- [Private modules](private-modules.md): files, databases, secrets, and protected work.
- [Calls reference](calls-reference.md): common frontend calls.
- [Modals](modals.md): HTML and native dialogs.
- [Building](building.md): create an app for release.
