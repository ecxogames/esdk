# Build the Desktop App or Website

## First-time setup

```bat
.\scripts\setup.bat
```

This prepares Python, project packages, WebView2 headers, CMake tools, and optional Docker support.

## Develop

```bat
.\scripts\dev.bat
```

Choose a fresh build after changing native engine files. Choose the previous build for the fastest launch.

## Create a release build

```bat
.\scripts\build.bat
```

Choose:

- **Installer** for a normal Windows setup file.
- **Standalone** for a portable folder with Python included.
- **Regular** for local testing.
- **Web** for browser-only UI output.

Web Publish compiles the shared `ui/` source into `dist/Web`. It removes `target="desktop"` elements, compiles TypeScript and Tailwind, minifies CSS, and mangles JavaScript. Upload the contents of `dist/Web` to a static web host.

Standalone and installer builds embed local CSS, JavaScript, images, and HTML pages into the app.

## Test with Docker

```bat
.\scripts\docker.bat
```

The command installs Docker Desktop when needed, starts it quietly, builds a clean container, installs `requirements.txt`, imports the backend, and runs tests from `tests/` when present.

Docker tests the Python application in isolation. The Windows WebView app itself still runs on Windows.

## Control refreshing

Set `CAN_REFRESH=true` in `properties.config` to allow F5, Ctrl+R, and context-menu refresh actions. Refreshing returns through `MAIN_PAGE`, including from client-side routes. Set it to `false` to disable those actions.
