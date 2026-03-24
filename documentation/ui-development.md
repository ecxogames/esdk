# UI Development: Navigation and Components

The ESD Suite Framework uses a standard Webview for its frontend. This means you can use standard web technologies (HTML, CSS, and JavaScript) to build your pages and components.

## 1. Navigation Between Pages

Navigating between different views works exactly like a traditional website. Since your files are loaded locally, you use relative paths to link pages together.

### Using HTML Links
If your `MAIN_PAGE` is set to `ui/pages/index.html` and you create a second page at `ui/pages/settings.html`, you can navigate to it using a standard anchor tag:

```html
<!-- Inside index.html -->
<a href="settings.html">Go to Settings</a>
```

### Using JavaScript
You can also trigger navigation programmatically using JavaScript's `window.location`:

```javascript
// Navigate to another page in the same folder
window.location.href = "settings.html";

// Navigate to a page in a different folder
window.location.href = "../os/example.html";
```

> **Note on Paths:** All relative paths are evaluated from the location of the *currently loaded* HTML file. 

---

## 2. Adding and Reusing Components

Without setting up a frontend framework (like React or Vue), the best way to reuse small pieces of UI (like the ones stored in `ui/components/`) is by dynamically loading them into your pages using JavaScript's native `fetch()` API.

### Step 1: Create a Component
Create your component file. For example, `ui/components/button.html`:
```html
<button style="background: blue; color: white; padding: 10px;">
    Click Me!
</button>
```

### Step 2: Create a Container in Your Page
In your main page (e.g., `ui/pages/index.html`), place an empty `<div>` where you want the component to appear:

```html
<div id="custom-button-container"></div>
```

### Step 3: Load the Component using Fetch
Use JavaScript to fetch the component and inject the HTML into the container:

```html
<script>
    // Since index.html is inside ui/pages, we go up one folder and into components
    fetch('../components/button.html')
        .then(response => response.text())
        .then(html => {
            document.getElementById('custom-button-container').innerHTML = html;
        })
        .catch(err => console.error('Failed to load component:', err));
</script>
```

### Advanced: Web Components
If you want encapsulated styles and custom tags like `<my-widget>`, you can use native browser Web Components:

```html
<script>
    class MyWidget extends HTMLElement {
        connectedCallback() {
            this.innerHTML = `<div style="border: 1px solid black; padding: 10px;">I am a custom widget!</div>`;
        }
    }
    customElements.define('my-widget', MyWidget);
</script>

<!-- Now use it anywhere in the HTML -->
<my-widget></my-widget>
```

---

## 3. Best Practices
* **Keep assets relative:** Use `./` or `../` for images, CSS, and JS files so they resolve correctly regardless of absolute deployment locations.
* **Component scripts:** When using `fetch()` to inject HTML, keep in mind that `<script>` tags inside the fetched HTML won't automatically execute. It is better to import your JS logic inside the main page or use Native Web Components for components that require heavy JS logic.