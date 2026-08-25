# Frontend Calls

## Call Python

```javascript
const result = await window.invokeBridge({ action: "ping", data: "hello" });
```

## Window controls

```javascript
window.minimizeWindow();
window.maximizeWindow();
window.closeWindow();
```

## Open an EDK desktop modal

```javascript
const answer = await window.openModal("confirm");
```

## Handle errors

```javascript
try {
    const response = await window.invokeBridge({ action: "load_data" });
    if (response.status !== "ok") throw new Error(response.reason);
    console.log(response.result);
} catch (error) {
    console.error(error.message);
}
```

Backend calls return promises, so use `await` inside an `async` function.
