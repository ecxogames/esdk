# Getting Started with ESDK

Welcome to the Ecxo Softwares Development (ESD) Suite! This framework is a cross-platform desktop application engine that bridges C++, Python, and JavaScript.

## Architecture Overview

ESDK uses three layers: a C++ engine for application lifecycle and native windowing, a Python backend for app logic, and an HTML/CSS/JavaScript frontend rendered in a WebView.

## Directory Structure

- `/engine/` - Core C++ runtime code (Entry point, window creation, webview integration).
- `/server/` - Python backend logic. Treated as private during compilation.
- `/ui/` - User interface code (HTML/CSS/JS entry points).
- `/public/` - Shared assets accessible by all layers.
- `/private/` - Restricted code (C++, JS, Python) accessible only via secure imports.
- `/scripts/` - Utility scripts for development and building.

## Build Requirements

To build the SDK, you need:

- CMake 3.14 or newer.
- A C++ compiler (MSVC on Windows, Clang/GCC on macOS/Linux).
- The Python version specified by `python==x.y.z` in `requirements.txt`, including development headers.

## Setting Up the Prototype

### 1. Run Setup

You have to install all the dependencies, but don't worry, the [`setup.py`](/scripts/setup.py) script does everything for you:

```bash
python scripts/setup.py
```

Setup installs the app's pip requirements and optionally creates a Docker test environment. Start development and choose Docker when prompted to run the backend tests in a newly created, disposable container:

On Windows, Docker setup automatically installs Docker Desktop through `winget` when necessary and adds the Docker CLI to your user `PATH`.

```bash
python scripts/dev.py
```

### 2. Build

To compile the C++ engine layer, run the [`build.py`](/scripts/build.py) script:

```bash
python scripts/build.py
```

### 3. Run the Application

Start testing the program by running the [`dev.py`](/scripts/dev.py) script, which will launch the application in development mode:

```bash
python scripts/dev.py
```

## Next Steps

Now you are ready to start developing your very own software using the ESDK! The application will launch with a simple UI, and you can begin customizing the frontend and backend logic as needed.

The published documentation is available at [docs.ecxo.ca](https://docs.ecxo.ca/#/category/esdk). The Markdown files in this folder are ready to import into that documentation website.
