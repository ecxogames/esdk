# Getting Started with ESD Suite

Welcome to the Ecxo Softwares Development (ESD) Suite! This framework is a cross-platform desktop application engine that bridges C++, Python, and JavaScript.

## Architecture Overview

The application is built on three core pillars:
1. **C++ (Engine Layer):** Handles native system interactions, window creation, and embeds both the webview and the Python runtime.
2. **Python (Backend Layer):** Serves as the application's backend logic, scripting engine, and AI integration point.
3. **JavaScript/HTML/CSS (Frontend Layer):** Powers the user interface, rendering inside the embedded webview.

### The Communication Bridge

The core of the engine is an Inter-Process Communication (IPC) bridge that routes data:
`JavaScript ↔ C++ ↔ Python`

- **Frontend to Backend:** JS calls an injected global function (`window.invokeBridge`), sending a JSON string. C++ intercepts this and passes it to the embedded Python interpreter.
- **Backend to Frontend:** Python processes the request and returns a JSON string to C++. C++ then resolves the original JS Promise with this response.

## Directory Structure

* `/engine/` - Core C++ runtime code (Entry point, window creation, webview integration).
* `/server/` - Python backend logic. Treated as private during compilation.
* `/ui/` - User interface code (HTML/CSS/JS entry points and components).
* `/public/` - Shared assets accessible by all layers.
* `/private/` - Restricted code (C++, JS, Python) accessible only via secure imports.
* `/scripts/` - Utility scripts for development and building.

## Build Requirements

To build the prototype, you need:
- CMake (3.14+)
- A C++ Compiler (MSVC on Windows, Clang/GCC on macOS/Linux)
- Python 3 (installed on the system with development headers/libs)

## Setting Up the Prototype

### 1. Fetch Dependencies & Configure Environment
We have provided an automated setup script that downloads the core `webview.h` header, fetches the required Microsoft WebView2 SDK natively via CMake, unconditionally checks for your compiler setup, and configures the `build` directory:
```bash
python scripts/setup_deps.py
```
*(Note: If the script fails to find CMake on Windows, it will safely attempt to download and install it for you).*

### 2. Build 
To compile the C++ engine layer, you just need to invoke the configured build tool:
```bash
cmake --build build
```

### 3. Run the Application
Run the executable from the project root (so it can find the `/server` and `/ui` folders):
```bash
# Windows
.\build\Debug\ESDEngine.exe

# macOS/Linux
./build/ESDEngine
```

When the window opens, click the button to test the `JS -> C++ -> Python` communication bridge!