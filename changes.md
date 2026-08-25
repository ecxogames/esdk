Here is a list of the changes made in this release:

## Developer Experience
- Added friendly PowerShell commands for setup, development, builds, Docker tests, packaging, and updates.
- Kept `scripts/` PowerShell-only and moved internal Python tooling under `engine/tooling/`.
- Renamed the shared PowerShell bootstrapper to `package.ps1` and removed its redundant package-only wrapper.
- Added automatic installation of the Python version requested by `requirements.txt` and automatic dependency synchronization.
- Simplified the documentation into short, focused guides with one clear example per concept.
- Added a documentation start page and replaced Python command examples with supported PowerShell commands.

## AMAS Reliability Improvements
- Prevented Windows from painting a white non-client border around frameless apps during navigation and DPI changes.
- Made rounded corners DPI-aware while preserving maximize, restore, resize, and snap behavior.
- Embedded local CSS, JavaScript, and image assets referenced by HTML pages.
- Split large embedded pages into compiler-safe chunks and made CMake rebuild them whenever UI files change.
- Added retry-safe cleanup for locked build and distribution folders, including project-scoped process shutdown.
- Made standalone builds use the requested Python development runtime and include Tcl/Tk for native dialogs.
- Decoded bridge payloads with Python's JSON parser so escaped strings and object arguments reach the backend correctly.
- Exposed the backend bridge inside ESDK modal WebViews as well as the main application window.

## Docker Reliability
- Made the Docker command install Docker Desktop automatically when it is missing.
- Kept Docker startup, installation, builds, and validation quiet and self-contained.
- Exposed clean-container dependency installation, backend imports, and optional tests through one PowerShell command.

## Native Window Management
- Changed native WebView windows to start hidden instead of briefly appearing at the library's default top-left position.
- Made splash screens, main windows, and modal windows apply their final style, DPI-aware size, monitor position, and content before becoming visible.
- Added document-ready native window activation so prepared windows appear centered on their first visible frame.
- Centered modal windows on the same monitor as their parent application.
- Hid the main window while transitioning from splash configuration to main-window configuration so the visible window never resizes or moves between layouts.
- Preserved the native Windows sizing frame behind frameless applications so maximize, restore, snap, minimize, and work-area calculations continue working with the titlebar hidden.
- Removed rounded window clipping while a frameless window is maximized so the WebView can fill the complete monitor work area.
- Reapplied the configured rounded region after restoring a frameless window to its normal size.
- Added rounded-region updates for native resize and DPI-change events.
- Fixed minimizing a maximized frameless window and restoring it without breaking the display or losing the later restore-to-normal behavior.
- Initialized WebView windows off-screen and revealed them only after the page rendered, preventing blank black or white startup surfaces.
- Refreshed native frame and child compositor surfaces during reveal so the first visible frame contains the application.

## Runtime And Application Configuration
- Added `APP_PORT` to `properties.config` so applications are no longer restricted to port 2024.
- Added native validation for configured ports with a safe fallback to port 2024 for missing or invalid values.
- Updated the embedded HTTP server, readiness check, splash navigation, main-page navigation, and development tooling to use the configured application port.
- Registered the splash-to-main bridge before the first WebView navigation to prevent initialization races.
- Added splash-side bridge polling so slower WebView initialization no longer leaves the splash screen visible indefinitely.
- Made each embedded server bind its port synchronously and automatically select an available fallback when the configured port is already occupied.

## Python Requirements And Portable Builds
- Added a project-level `requirements.txt` with an explicit `python==` runtime directive and support for normal pip dependencies.
- Added shared requirement parsing, Python version resolution, interpreter compatibility validation, and temporary pip requirement generation.
- Added Python dependency installation to the environment setup flow.
- Made regular and standalone builds retain the project's requirements file.
- Changed standalone builds to download the Python runtime version requested by the project instead of assuming the current patch version.
- Configured embedded Python to load `site` and its bundled `Lib\\site-packages` directory.
- Added pip bootstrapping and application dependency installation inside standalone distributions.
- Added public and private Python modules to standalone builds.
- Improved standalone failure handling and prevented installer creation after a failed portable build.

## Docker Development Tests
- Added disposable Docker validation for ESDK applications.
- Added Docker CLI and Docker Desktop discovery across system and user installation locations.
- Added Docker engine readiness checks with startup progress and timeout handling.
- Added automatic Docker Desktop installation support through Windows Package Manager.
- Added optional Docker CLI registration in the user's PATH.
- Added generated Dockerfile and `.dockerignore` development configuration.
- Added clean container tests for Python compilation, backend imports, application requirements, and project structure.
- Added Docker testing to fresh development builds before local compilation.
- Added interactive setup controls so Docker validation can be enabled or skipped.
- Started Docker Desktop through its detached command-line interface so its dashboard window does not open during setup.
- Hid Docker build, run, readiness, and installer processes on Windows and reduced their console output.
- Requested Winget's silent installation mode when Docker Desktop must be installed.

## Development Workflow
- Added `requirements.txt` to watched development files.
- Changed port cleanup to read and release the configured `APP_PORT` instead of a hard-coded port.
- Added Docker validation to fresh builds while keeping previous-build launches available.
- Improved development messages for container setup failures and configured-port cleanup.

## Build And Installer Packaging
- Added selectable installer filenames using `Installer.exe`, the dated Ecxo Software naming convention, or a sanitized custom name.
- Changed generated Inno Setup output to use the selected installer filename consistently.
- Ensured installers always rebuild the latest standalone application before packaging.
- Added clearer standalone and installer success and failure results.
- Kept runtime requirements, backend modules, configuration, UI files, and Visual C++ runtime dependencies together in portable output.

## Release Packaging
- Added an official release mode and a local test-archive mode.
- Added local `esd-engine-test.zip` creation without requiring a Git tag or GitHub upload.
- Added automatic remote tag refresh before resolving release versions.
- Added support for both `v0.0.0` and `0.0.0` tag naming conventions.
- Renamed official release archives to the `esdk-{version}.zip` convention.
- Added support for updating an existing GitHub release instead of failing when it already exists.
- Added release title and notes updates plus replacement of existing ZIP assets.
- Added cleanup for legacy `esd-engine-{version}.zip` release assets.
- Improved tag, archive, GitHub CLI, and upload error reporting.

## Documentation
- Added backend and JavaScript-to-Python bridge documentation with request, response, action, and module-routing examples.
- Added a complete calls reference for window controls, frontend modals, backend calls, navigation, and external links.
- Added frontend HTML modal and native Python dialog documentation.
- Added public-module documentation with structure, imports, examples, and public/private guidance.
- Added private-module documentation with structure, server integration, examples, and security guidance.
- Expanded building documentation for installers, standalone output, regular builds, configurable ports, and Docker tests.
- Updated getting-started documentation for the current architecture, setup, build, and runtime workflow.
- Updated UI development guidance for navigation and web components.
