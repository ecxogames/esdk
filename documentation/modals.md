# Custom Modals

ESDK provides two complementary modal systems: **HTML modals** that open as real native OS windows, and **native system dialogs** called from Python. Both replace the default browser `alert()` / `prompt()` / `confirm()` with styled, controllable alternatives.

## 1. HTML Modals (Frontend)

HTML modals are template files stored in `ui/modals/`. When opened, the engine spawns a **native OS window** on its own thread — completely separate from the main app window. The modal can have a custom HTML titlebar (no OS chrome) or the standard OS titlebar, controlled by the `<modal>` and `<titlebar>` elements.

### Calling a Modal from JavaScript

```javascript
// Returns a Promise that resolves when the modal calls closeModal()
window.openModal('alert').then(function (result) {
    console.log('Modal closed with:', result);
});

// Or with async/await
const result = await window.openModal('prompt');
if (result !== null) {
    console.log('User entered:', result);
}
```

### Template File Format

Each modal lives in `ui/modals/{name}.html`. The outer `<modal>` element controls the OS window; inner sections define the content:

```html
<modal width="420" height="240" blur="true" closeable="true" titlebar="true">

    <!-- Custom HTML titlebar (value="false" = no OS chrome) -->
    <titlebar value="false" height="40">
        <div style="background:#111; display:flex; align-items:center; padding:0 14px; height:100%; color:#fff;">
            My Dialog
            <button onclick="Close()" style="margin-left:auto;">&times;</button>
        </div>
    </titlebar>

    <!-- OS native titlebar (value="true") -->
    <!-- <titlebar value="true"></titlebar> -->

    <title><value>My Dialog</value></title>

    <content>
        <div style="padding:28px; text-align:center; color:#fff;">
            <h2>Hello!</h2>
            <button onclick="closeModal('ok')">OK</button>
        </div>
    </content>

    <script>
        function Close() { closeModal(null); }
    </script>
</modal>
```

#### <modal> attributes

| Attribute | Type | Description |
| --- | --- | --- |
| `width` | number | Window width in logical pixels |
| `height` | number | Window height in logical pixels |
| `blur` | boolean | Dims and blurs the parent window while the modal is open |
| `closeable` | boolean | Whether the OS close button is enabled (native titlebar only) |
| `titlebar` | boolean | Presence of any titlebar (native or custom) |

#### <titlebar> attributes

| Attribute | Type | Description |
| --- | --- | --- |
| `value` | `"false"` / `"true"` | `false` = custom HTML titlebar, no OS chrome; `true` = OS native titlebar |
| `height` | number | Height of the custom titlebar drag region in pixels (only when `value="false"`) |

### Rounded Corners

Frameless modals (custom titlebar) automatically inherit the `CORNER_RADIUS` value from `ui/modals/properties.config`. Set it there to apply rounded corners to all frameless modal windows.

```ini
# ui/modals/properties.config
CORNER_RADIUS=20
```

### Built-in Modals

| File | Purpose | Titlebar | Returns |
| --- | --- | --- | --- |
| `alert.html` | Simple dismissal dialog | Custom HTML | `null` |
| `prompt.html` | Text input dialog | OS native | string or `null` |
| `custom.html` | Blank starter template | OS native | `true` / `false` |

### Closing a Modal

Call `closeModal(value)` from inside a modal's `<script>` block. The value is forwarded to the parent's Promise. Pass `null` to indicate cancellation.

```javascript
function Submit() {
    var input = document.getElementById('modal-input').value;
    closeModal(input);   // resolves with the user's text
}
function Cancel() {
    closeModal(null);    // resolves with null
}
```

### Creating a Custom Modal

Duplicate `ui/modals/custom.html`, rename it, and update the sections. No C++ changes are needed.

```html
<!-- ui/modals/confirm-delete.html -->
<modal width="400" height="200" blur="true" closeable="false">
    <titlebar value="true"></titlebar>
    <title><value>Confirm Delete</value></title>
    <content>
        <div style="padding:28px; text-align:center; color:#fff; font-family:system-ui,sans-serif;">
            <h2>Delete Item?</h2>
            <p style="color:#9ca3af">This action cannot be undone.</p>
            <button onclick="closeModal(false)">Cancel</button>
            <button onclick="closeModal(true)">Delete</button>
        </div>
    </content>
    <script></script>
</modal>
```

```javascript
// Calling your custom modal
const confirmed = await window.openModal('confirm-delete');
if (confirmed) deleteItem();
```

## 2. Native System Dialogs (Python Backend)

The `public/modals.py` module wraps **tkinter** system dialogs. These are native OS windows — not WebView — so they work even before the main window is ready, during background tasks, or whenever you need the OS to render the dialog. Each call **blocks the calling thread** until the user dismisses the dialog, then returns the result synchronously.

### Importing

```python
from public import modals
```

### Function Reference

| Function | Parameters | Returns | Dialog type |
| --- | --- | --- | --- |
| `show_alert(title, message)` | `title: str`, `message: str` | `None` | Warning — single OK button |
| `show_info(title, message)` | `title: str`, `message: str` | `None` | Information — single OK button |
| `show_error(title, message)` | `title: str`, `message: str` | `None` | Error — single OK button |
| `show_confirm(title, message)` | `title: str`, `message: str` | `bool` | Yes / No — returns `True` if Yes |
| `show_prompt(title, message, default="")` | `title: str`, `message: str`, `default: str` | `str | None` | Text input — returns the string, or `None` if cancelled |

### show_alert

Shows a native OS warning dialog. Blocks until the user clicks OK.

```python
modals.show_alert("Low Disk Space", "Less than 500 MB remaining. Please free up space.")
```

### show_info

Shows a native OS information dialog. Blocks until the user clicks OK.

```python
modals.show_info("Export Complete", "Your file has been saved to the Downloads folder.")
```

### show_error

Shows a native OS error dialog. Blocks until the user clicks OK.

```python
modals.show_error("Connection Failed", "Could not reach the server. Check your network and try again.")
```

### show_confirm

Shows a native OS Yes / No dialog. Returns `True` if the user clicks Yes, `False` if they click No.

```python
confirmed = modals.show_confirm("Delete Item", "This action cannot be undone. Continue?")
if confirmed:
    delete_item()
```

### show_prompt

Shows a native OS text-input dialog. Returns the entered string, or `None` if the user cancels. Supply `default` to pre-fill the input field.

```python
name = modals.show_prompt("Rename File", "Enter a new name:", default="untitled")
if name is not None:
    rename_file(name)
```

### Calling from the Bridge

Register an action in `server/api.py` to expose any modal to the JavaScript frontend. The bridge Promise resolves once the user dismisses the dialog and the Python thread unblocks.

#### Python — server/api.py

```python
from public import modals

def handle_message(message_str):
    req    = json.loads(message_str)
    action = req.get("action")

    # Blocking alert — resolves with null once dismissed
    if action == "modal_alert":
        modals.show_alert(req.get("title", "Alert"), req.get("message", ""))
        return json.dumps({"status": "ok", "result": None})

    # Blocking info dialog
    elif action == "modal_info":
        modals.show_info(req.get("title", "Info"), req.get("message", ""))
        return json.dumps({"status": "ok", "result": None})

    # Blocking error dialog
    elif action == "modal_error":
        modals.show_error(req.get("title", "Error"), req.get("message", ""))
        return json.dumps({"status": "ok", "result": None})

    # Yes/No confirm — result is true or false
    elif action == "modal_confirm":
        confirmed = modals.show_confirm(req.get("title", "Confirm"), req.get("message", ""))
        return json.dumps({"status": "ok", "result": confirmed})

    # Text prompt — result is the string, or null if cancelled
    elif action == "modal_prompt":
        value = modals.show_prompt(req.get("title", "Input"), req.get("message", ""), req.get("default", ""))
        return json.dumps({"status": "ok", "result": value})
```

#### JavaScript — calling from the UI

```javascript
// Alert — resolves once dismissed
await window.invokeBridge({ action: 'modal_alert', title: 'Warning', message: 'Disk space is low.' });

// Info
await window.invokeBridge({ action: 'modal_info', title: 'Done', message: 'Export complete.' });

// Error
await window.invokeBridge({ action: 'modal_error', title: 'Error', message: 'Connection failed.' });

// Confirm — result.result is true (Yes) or false (No)
const { result: confirmed } = await window.invokeBridge({
    action: 'modal_confirm',
    title: 'Delete Item',
    message: 'This cannot be undone. Continue?'
});
if (confirmed) deleteItem();

// Prompt — result.result is the entered string, or null if cancelled
const { result: name } = await window.invokeBridge({
    action: 'modal_prompt',
    title: 'Rename',
    message: 'Enter a new name:',
    default: 'untitled'
});
if (name !== null) renameItem(name);
```

### Blocking Behaviour

Every function in `modals.py` blocks the Python thread until the dialog is dismissed. This means:

- The bridge request will not return until the user responds — the JavaScript `await` naturally waits for it.
- No other bridge calls can be processed on that thread while a dialog is open.
- Do not call modals from a background thread that owns resources locked by the main thread, as this can cause a deadlock.

### When to Use Each System

|  | HTML Modals | Python (tkinter) Dialogs |
| --- | --- | --- |
| **Triggered from** | JavaScript frontend | Python backend or via bridge |
| **Appearance** | Fully custom (CSS) | Native OS look & feel |
| **Return value** | Via Promise (`closeModal`) | Synchronous Python return |
| **Works before webview loads** | No | Yes |
| **Best for** | In-app UX flows, styled dialogs | Backend errors, startup checks, background tasks |
