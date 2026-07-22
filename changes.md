Here is a list of the changes made in this release:

## Runtime And Application Configuration
- Added `APP_PORT` to `properties.config` so applications are no longer restricted to port 2024.
- Added native validation for configured ports with a safe fallback to port 2024 for missing or invalid values.
- Updated the embedded HTTP server, readiness check, splash navigation, main-page navigation, and development tooling to use the configured application port.
- Registered the splash-to-main bridge before the first WebView navigation to prevent initialization races.
- Added splash-side bridge polling so slower WebView initialization no longer leaves the splash screen visible indefinitely.

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
