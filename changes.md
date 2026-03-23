Here is a list of the changes made in this release:

## Compiler And Build Pipeline
- Replaced the native C++ compiler launcher with a Python-only EWDK toolchain.
- Added browser-ready page compilation from EWDK `<template>`, `<style>`, and `<script>` blocks.
- Added TypeScript compilation for scripts, functions, and classes with ES module output.
- Added JavaScript and MJS compression and top-level mangling through Terser for production builds.
- Added CSS minification for builds that do not use Tailwind.
- Preserved page HTML content while wrapping it in a standard browser document with metadata and a generated title.
- Added clean and incremental build options through `--no-clean` and `--no-optimize`.
- Added an `ewdk-manifest.json` file that records the entry page, optimization state, and Tailwind state.
- Changed temporary builds to use isolated per-build staging directories so concurrent compiler processes cannot delete each other's files.
- Added clearer compiler failures when required programs or npm tools are unavailable.

## Tailwind CSS
- Added first-class Tailwind support when `tailwind`, `tailwindcss`, or `@tailwindcss/cli` is listed in `requirements.txt`.
- Made the installer resolve the `tailwind` alias to the official `tailwindcss` and `@tailwindcss/cli` packages.
- Added optional Tailwind version forwarding from the EWDK requirements format.
- Added Tailwind source scanning across pages, components, scripts, functions, classes, modules, and standalone stylesheets.
- Added support for Tailwind utilities in complete HTML, TypeScript, JavaScript, and MJS class strings.
- Added support for Tailwind directives such as `@apply` in page, component, and standalone CSS.
- Added a generated `ewdk.css` stylesheet and automatic stylesheet links for root and nested pages.
- Added production Tailwind minification while retaining readable development output.
- Added Tailwind usage examples to the example component, page scripts, requirements, and README.

## Development Server And Live Reload
- Added a Python development server that builds and serves the browser-ready `dist` directory.
- Added automatic source watching and rebuilding for pages, components, scripts, functions, classes, modules, configuration, and requirements.
- Changed file detection to hash source contents so rapid and same-size edits are not missed.
- Added a lightweight live-reload endpoint and injected client that refreshes connected browsers after a successful build.
- Disabled development caching for HTML, CSS, JavaScript, modules, and other served assets so rebuilt files are fetched immediately.
- Kept the last successful distribution available when a source edit temporarily fails to compile.
- Reduced default console output by hiding compiler subprocess and routine HTTP request logs.
- Added `--verbose` for TypeScript, Tailwind, and HTTP diagnostics when debugging.
- Added development options for host, port, browser opening, and watch interval.

## Dependencies And Installation
- Added npm dependency installation driven by EWDK's `requirements.txt`.
- Added support for dependency versions using the `package=version` format.
- Added automatic creation of the local private `package.json` file.
- Added TypeScript and Tailwind shortcut installation commands.
- Added TypeScript, Terser, Tailwind, and the Tailwind CLI as the compiler dependencies.
- Added npm build artifacts and temporary compiler directories to `.gitignore`.

## Modal Function And Browser APIs
- Added a reusable custom HTML modal implementation in `functions/Modal.ts`.
- Added configurable titles, HTML content, confirm text, cancel text, cancel visibility, and backdrop behavior.
- Added Promise-based confirmation results so callers can react to confirm and dismiss actions.
- Added close-button, Escape-key, cancel-button, confirm-button, and optional backdrop closing.
- Added accessible dialog roles, modal labeling, initial button focus, animations, and one-time style injection.
- Kept the options-based `showModal({ ... })` API for reusable scripts.
- Added a namespace-style `Modal.showModal(title, html)` API for direct page imports.
- Exported `Modal` and `showModal` together so both invocation styles remain supported.
- Fixed the page import to use the emitted `Modal.js` filename casing so it works on case-sensitive deployment hosts.
- Updated the example page to demonstrate importing and opening the modal directly from a module script.

## Example Project
- Added a reusable event bridge class for communication between independent application features.
- Added a shared ES module with a title-formatting utility.
- Added a populated TypeScript entry script that demonstrates the modal, bridge, modules, and Tailwind classes.
- Added a reusable example HTML component with component markup, styles, behavior, and Tailwind `@apply` directives.
- Added a browser-ready example page with inline styles, Tailwind utilities, templates, and ES module imports.

## Packaging And Reference Generation
- Added deployable ZIP creation from the compiled `dist` directory.
- Added configurable package archive names.
- Added Markdown reference generation from JSDoc blocks in scripts, functions, classes, and modules.
- Added command-line help and error handling for building, development, installation, packaging, and reference generation.

## Project Cleanup And Documentation
- Removed the ESDK-specific `public` and `ui` directories from the web development kit.
- Removed the unused C++ `main.cpp` compiler and CMake project definition.
- Corrected the configured main page away from the removed ESDK UI path.
- Replaced the desktop ESDK README with Python-only EWDK setup, development, build, package, reference, structure, and Tailwind documentation.
- Simplified `.gitignore` by removing obsolete ESDK Python cache paths.
