# Building and Distributing

The `build.py` script manages the distribution process. Run it in the `main` directory:

```bash
python build.py
```

## Build Options

### 1. Installer (Production)

Generates a self-contained Portable build and automatically compiles an `.exe` installer. Requires [Inno Setup](https://jrsoftware.org/isdl.php).

Before building, select one of these output names:

- `Installer.exe`
- Ecxo Software convention: `software-name-YYYYMMDD.exe`
- A custom filename

### 2. Standalone (Portable)

Builds a `dist/Standalone` directory with a self-contained Python runtime alongside your application. Requires no installation—just zip and share.

Set the runtime and packages in the root `requirements.txt`:

```text
python==3.11.9
requests==2.32.4
```

The build downloads the requested embeddable Python patch version and installs every normal pip requirement into it. Run the build script with the same Python major/minor version requested in the file.

### 3. Regular (Local Dev)

Standard local CMake build. Warning: Dependent on your system's Python path. Do not distribute this version.

## Distribution Structure

When distributing manually, keep this structure:

```text
YourApp/
 ├── ESDEngine.exe         (Core Engine)
 ├── properties.config     (Core Settings)
 ├── python3.dll           (Embedded Python)
 ├── python311.zip         (Standard library)
 ├── requirements.txt     (Python runtime and packages)
 └── server/              (Backend)
```

## Application Port

Set the WebView's local application server port in `properties.config`:

```ini
APP_PORT=2024
```

Valid values are `1` through `65535`; invalid values fall back to `2024`.

## Disposable Docker Tests

Choose Docker setup when running `python scripts/setup.py`, then start development:

```bash
python scripts/dev.py
```

Answer yes when `dev.py` asks whether to use Docker. Each Docker invocation builds the current app snapshot and launches it in a new `--rm` container. The container compiles and imports the backend, then discovers `tests/test_*.py`. The interactive Windows WebView2 GUI still runs on the host because Docker cannot display a desktop WebView window.

During Windows setup, a missing Docker Desktop installation is elevated through a UAC prompt and installed with `winget`, and its CLI directory is saved to the user `PATH`. Setup and `dev.py` automatically start Docker Desktop when its engine is stopped and wait for the Docker API before continuing.
