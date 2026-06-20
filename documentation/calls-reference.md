# Calls Reference

ESDK exposes a set of native JavaScript bindings that let your frontend HTML control the OS window and communicate with the C++ and Python layers. All bindings are available globally on the `window` object and are injected before `window.onload` fires.

## Window Control

### `windowClose()`

Closes the native app window using the standard OS close flow. Returns `void`.

```javascript
if (window.windowClose) window.windowClose();
```

### `windowMinimize()`

Minimizes the app to the taskbar. This requires `CAN_MINIMIZE=true` in `properties.config`. Returns `void`.

```javascript
if (window.windowMinimize) window.windowMinimize();
```

### `windowMaximize()`

Toggles between maximized and restored window states. Returns `void`.

```javascript
if (window.windowMaximize) window.windowMaximize();
```

### `dragWindow()`

Starts a native window drag. Bind it to `onmousedown` on a custom titlebar or drag handle.

```html
<div onmousedown="if(window.dragWindow) window.dragWindow()">Drag here</div>
```

## Modal System

### `openModal(name)`

Opens `ui/modals/<name>.html` as a native window and returns a `Promise` that resolves when the modal closes. A missing modal resolves to `null`.

```javascript
const result = await window.openModal('prompt');
```

### `closeModal(value)`

Available inside modal scripts. Closes the modal and resolves the parent's `openModal()` Promise with `value`.

```javascript
function Submit() {
    closeModal(document.getElementById('input').value);
}
```

## Backend Bridge

### `invokeBridge(payload)`

Passes an object to `server/api.py` and resolves with its parsed JSON response. The payload must include an `action` field.

```javascript
const response = await window.invokeBridge({ action: 'ping', data: 'hello' });
console.log(response.result);
```

## Navigation and Links

### `openExternalLink(url)`

Opens a fully-qualified HTTP or HTTPS URL in the default browser. Normal external `<a>` clicks are routed through this binding automatically.

```javascript
window.openExternalLink('https://docs.ecxo.ca/#/category/esdk');
```

## Quick Reference

| Call | Available in | Returns |
| --- | --- | --- |
| `windowClose()` | Main window | `void` |
| `windowMinimize()` | Main window | `void` |
| `windowMaximize()` | Main window | `void` |
| `dragWindow()` | Main window and modals | `void` |
| `openModal(name)` | Main window | `Promise<any>` |
| `closeModal(value)` | Modal windows | `void` |
| `invokeBridge(payload)` | Main window | `Promise<object>` |
| `openExternalLink(url)` | Main window | `void` |
