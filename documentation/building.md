# Build the App

## First-time setup

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

This prepares Python, project packages, WebView2 headers, CMake tools, and optional Docker support.

## Develop

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

Choose a fresh build after changing native engine files. Choose the previous build for the fastest launch.

## Create a release build

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1
```

Choose:

- **Installer** for a normal Windows setup file.
- **Standalone** for a portable folder with Python included.
- **Regular** for local testing.
- **Web** for browser-only UI output.

Standalone and installer builds embed local CSS, JavaScript, images, and HTML pages into the app.

## Test with Docker

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\docker.ps1
```

The command installs Docker Desktop when needed, starts it quietly, builds a clean container, installs `requirements.txt`, imports the backend, and runs tests from `tests/` when present.

Docker tests the Python application in isolation. The Windows WebView app itself still runs on Windows.
