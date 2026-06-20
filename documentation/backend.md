# Backend & Server Layer

The server layer is the central entry point for all Python backend logic in an ESDK application. Every message sent from the JavaScript frontend passes through `server/api.py` before being routed to the appropriate module.

## How the Bridge Works

ESDK connects the JavaScript UI to Python via a C++ bridge. The flow for every call is:

```
JavaScript (UI)
    └─▶  window.invokeBridge({ action: "...", ...params })
              │
              ▼
         C++ Engine (engine/main.cpp)
              │  strips webview's JSON array wrapper
              │  passes raw JSON string to Python
              ▼
         server/api.py  →  handle_message(message_str)
              │
              ├─▶  public/   (non-sensitive helpers)
              └─▶  private/  (sensitive operations)
```

The C++ side returns whatever string Python returns, and the bridge resolves the JavaScript `Promise` with the parsed JSON object.

## The `handle_message` Function

`server/api.py` exports a single function that the engine calls for every bridge request:

```python
import json
from public import utils
from private import secret_processor

def handle_message(message_str):
    try:
        req = json.loads(message_str)
        action = req.get("action")

        if action == "ping":
            data = req.get("data", "")
            return json.dumps({"status": "ok", "result": f"Pong! I received: {data}"})

        elif action == "public_demo":
            greeting = utils.generate_greeting(req.get("name", ""))
            return json.dumps({"status": "ok", "result": greeting})

        elif action == "private_demo":
            result = secret_processor.process_secure_data(req.get("secret_data", ""))
            return json.dumps({"status": "ok", "result": result})

        return json.dumps({"status": "error", "reason": "Unknown action"})
    except Exception as e:
        return json.dumps({"status": "error", "reason": str(e)})
```

Every response must be a valid JSON string. The convention is `{"status": "ok", "result": ...}` on success and `{"status": "error", "reason": "..."}` on failure.

## Request & Response Format

### Request (JavaScript → Python)

Pass a plain JavaScript object to `invokeBridge`. It must contain an `action` string and any additional parameters your handler needs:

```javascript
window.invokeBridge({ action: "my_action", param1: "value", param2: 42 })
```

The C++ layer wraps this in a JSON array for transport and then strips the wrapper before handing the raw object string to Python. Python receives it as:

```json
{"action": "my_action", "param1": "value", "param2": 42}
```

### Response (Python → JavaScript)

Always return a `json.dumps` string. The bridge resolves the Promise with the parsed object, so in JavaScript `res` will be a plain object:

```javascript
window.invokeBridge({ action: "my_action", param1: "hello" })
    .then(res => {
        if (res.status === "ok") {
            console.log(res.result);   // your return value
        } else {
            console.error(res.reason); // error message
        }
    })
    .catch(err => console.error("Bridge error:", err));
```

## Adding a New Action

To expose new Python functionality to the UI, add an `elif` block inside `handle_message`:

```python
elif action == "get_version":
    version = req.get("channel", "stable")
    return json.dumps({"status": "ok", "result": f"1.0.0-{version}"})
```

Then call it from JavaScript:

```javascript
window.invokeBridge({ action: "get_version", channel: "beta" })
    .then(res => console.log(res.result)); // "1.0.0-beta"
```

For anything beyond a few lines of logic, keep `handle_message` thin and delegate to a module in `public/` or `private/`.

## Routing to Modules

Import your modules at the top of `server/api.py` and call them inside the relevant action handler:

```python
from public import utils          # non-sensitive helpers
from private import secret_processor  # sensitive operations

elif action == "greet":
    return json.dumps({"status": "ok", "result": utils.generate_greeting(req.get("name"))})

elif action == "save":
    return json.dumps({"status": "ok", "result": secret_processor.process_secure_data(req.get("data"))})
```

See [Public Modules](public-modules.md) and [Private Modules](private-modules.md) for guidance on what belongs in each layer.
