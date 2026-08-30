# Shared Desktop and Web UI

Build every page in `ui/`. EDK compiles the same HTML, CSS, JavaScript, TypeScript, components, and Tailwind classes for desktop and web.

## Folders

```text
ui/
├── pages/       App and website pages
├── components/  Reusable HTML
├── functions/   TypeScript or JavaScript functions
├── classes/     Shared classes and state
├── modules/     JavaScript modules
├── scripts/     Page scripts
├── styles/      CSS
├── themes/      Theme CSS
├── modals/      Desktop modal pages
└── splash/      Desktop splash page
```

## Desktop-only elements

```html
<div class="window-controls" target="desktop">
    <button onclick="window.windowMinimize()">Minimize</button>
    <button onclick="window.windowClose()">Close</button>
</div>
```

The element and everything inside it are included in desktop builds and removed from web builds.

Use `target="web"` for the inverse:

```html
<a href="/download" target="web">Download the desktop app</a>
```

Normal link targets such as `target="_blank"` are left unchanged.

## TypeScript

Create `ui/functions/example.ts`:

```ts
export function greet(name: string): string {
    return `Hello, ${name}!`;
}
```

Import the generated JavaScript from a page:

```html
<script type="module">
    import { greet } from "../functions/example.js";
    console.log(greet("EDK"));
</script>
```

## Tailwind

Tailwind is included with EDK. Use its classes directly in pages, components, scripts, or TypeScript-generated markup:

```html
<button class="rounded-lg bg-blue-600 px-4 py-2 text-white">Continue</button>
```

## Builds

Run `scripts/dev.bat` for the desktop app. Choose **Web Publish** in `scripts/build.bat` to create the browser-ready site in `dist/Web`.
