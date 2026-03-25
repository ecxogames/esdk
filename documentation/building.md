# Building and Distributing

The `build.py` script manages the distribution process. Run it in the `main` directory:

```bash
python build.py
```

## Build Options

### 1. Installer (Production)
Generates a self-contained Portable build and automatically compiles an `.exe` installer. Requires [Inno Setup](https://jrsoftware.org/isdl.php).

### 2. Standalone (Portable)
Builds a `dist/Standalone` directory with a self-contained Python runtime alongside your application. Requires no installation—just zip and share.

### 3. Regular (Local Dev)
Standard local CMake build. Warning: Dependent on your system's Python path. Do not distribute this version.

## Distribution Structure
When distributing manually, keep this structure:

```text
📁 YourApp/
 ├── ESDEngine.exe         (Core Engine)
 ├── properties.config     (Core Settings)
 ├── python3.dll           (Embedded Python)
 ├── python311.zip         (Standard library)
 ├── 📁 ui/                (Frontend)
 └── 📁 server/            (Backend)
```

**Note:** Pip dependencies for your backend aren't copied automatically. You must bundle them in a `site-packages` folder or install them into the embeddable Python environment before distribution.