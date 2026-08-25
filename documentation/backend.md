# Python Backend

The Python backend runs while the desktop app is open. JavaScript asks it to do work through the EDK bridge.

## Request flow

```text
JavaScript -> EDK bridge -> server/api.py -> public/ or private/ -> JavaScript
```

## Small example

Add an action to `server/api.py`:

```python
import json

def handle_message(message):
    request = json.loads(message)

    if request.get("action") == "greet":
        name = request.get("name", "friend")
        return json.dumps({"status": "ok", "result": f"Hello, {name}!"})

    return json.dumps({"status": "error", "reason": "Unknown action"})
```

Call it from the page:

```javascript
const response = await window.invokeBridge({ action: "greet", name: "Alex" });
console.log(response.result);
```

Keep `server/api.py` small. Put longer work in `public/` or `private/` and call it from the action.

The backend answers frontend requests. It does not directly change HTML on its own; return a result and let JavaScript update the page.
