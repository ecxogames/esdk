# Modals

ESDK supports HTML modals and native Windows dialogs.

## HTML modal

Place a modal page in `ui/modals/`, then open it from JavaScript:

```javascript
const result = await window.openModal("confirm");
```

Use HTML modals when the dialog should match your app's design.

## Native dialog

Use `public/modals.py` from a backend action:

```python
from public import modals

if action == "confirm_delete":
    confirmed = modals.show_confirm("Delete", "Delete this item?")
    return json.dumps({"status": "ok", "result": confirmed})
```

Call it from JavaScript:

```javascript
const response = await window.invokeBridge({ action: "confirm_delete" });
if (response.result) console.log("Confirmed");
```

Use native dialogs for simple operating-system messages. They pause that backend call until the user answers.
