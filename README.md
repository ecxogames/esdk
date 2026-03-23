# EWDK

EWDK is a Python-driven development kit for building browser applications from pages, components, TypeScript functions and classes, and ES modules.

## Setup

Node.js and Python 3 are required. Install the local TypeScript and optimization tools once:

```powershell
python engine/install.py
```

## Develop

```powershell
python engine/dev.py
```

The development server builds the source into `dist`, opens the application, watches the project, and automatically reloads connected browsers after changes. Use `--no-open`, `--host`, or `--port` to customize it.

## Build and package

```powershell
python engine/build.py
python engine/package.py --name my-app
python engine/reference.py
```

Production builds compile TypeScript, minify CSS, and compress and mangle JavaScript. Page HTML is converted into a standard browser document without HTML minification. Packaging creates a zip from `dist`, and reference generation writes JSDoc documentation to `reference/README.md`.

## Tailwind CSS

Add `tailwind` to `requirements.txt`, then install and build normally:

```powershell
python engine/install.py
python engine/dev.py
```

EWDK installs Tailwind's official packages, scans pages, components, scripts, functions, classes, modules, and CSS files, and injects the generated `ewdk.css` into every page. Tailwind utility classes can therefore appear in HTML or in complete class-name strings inside TypeScript and JavaScript. Inline and standalone CSS also support Tailwind directives such as `@apply`.

## Project structure

- `pages/`: application entry pages
- `components/`: reusable HTML components
- `scripts/`: page entry scripts
- `functions/`: reusable TypeScript functions
- `classes/`: reusable TypeScript classes
- `modules/`: JavaScript ES modules
- `engine/`: Python compiler, development, packaging, and documentation tools
