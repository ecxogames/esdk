# EDK Documentation

EDK builds desktop apps and websites from one shared UI, with an embedded Python backend for desktop features.

## Start here

1. Run `.\scripts\setup.bat` once.
2. Edit `ui/pages/index.html`.
3. Run `.\scripts\dev.bat`.

The batch commands find or install the requested Python version and install the packages in `requirements.txt` for you.

## Guides

- [Backend](backend.md): call Python from JavaScript.
- [Public modules](public-modules.md): reusable, non-sensitive Python code.
- [Private modules](private-modules.md): files, databases, secrets, and protected work.
- [Calls reference](calls-reference.md): common frontend calls.
- [Modals](modals.md): HTML and native dialogs.
- [Building](building.md): create an app for release.
