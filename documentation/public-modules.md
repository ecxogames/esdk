# Public Modules

The `public/` directory is for Python code that provides general-purpose, non-sensitive helper logic. Functions here are safe to call from anywhere in the backend — they do not touch the file system, databases, credentials, or any other sensitive resource.

## What Belongs in `public/`

- String formatting and text processing helpers
- Data transformation utilities (sorting, filtering, mapping)
- Calls to public, unauthenticated external APIs
- App metadata and configuration constants
- Validation helpers (email format checks, length limits, etc.)

If your function touches the file system, a database, an API key, or any secret — move it to [`private/`](private-modules.md) instead.

## File Structure

```
public/
└── utils.py        ← default helpers module (extend this or add new files)
```

You can add as many `.py` files as you need. Each file becomes its own importable module (e.g. `public/formatter.py` is imported as `from public import formatter`).

## The Default Module: `utils.py`

The template ships with `public/utils.py` containing two example functions:

```python
# public/utils.py

def generate_greeting(name):
    if not name:
        return "Hello, anonymous user!"
    return f"Hello, {name}! Welcome to the ESD Suite Framework."

def get_app_info():
    return {
        "version": "1.0.0",
        "description": "Cross-platform runtime with embedded Python."
    }
```

`generate_greeting` is a simple text formatter — exactly the kind of logic that belongs in `public/`. `get_app_info` returns static metadata that the UI can display without any security concern.

## Importing Public Modules in the Server

Import at the top of `server/api.py` and call inside an action handler:

```python
from public import utils

def handle_message(message_str):
    ...
    elif action == "public_demo":
        greeting = utils.generate_greeting(req.get("name", ""))
        return json.dumps({"status": "ok", "result": greeting})
```

You can import multiple public modules in the same file:

```python
from public import utils
from public import formatter
from public import validators
```

## Adding a New Public Function

**Step 1** — Add the function to an existing or new file inside `public/`:

```python
# public/utils.py

def format_currency(amount, symbol="$"):
    return f"{symbol}{amount:,.2f}"
```

**Step 2** — Add an action handler in `server/api.py`:

```python
elif action == "format_currency":
    amount = req.get("amount", 0)
    result = utils.format_currency(amount)
    return json.dumps({"status": "ok", "result": result})
```

**Step 3** — Call it from JavaScript:

```javascript
window.invokeBridge({ action: "format_currency", amount: 1234.5 })
    .then(res => console.log(res.result)); // "$1,234.50"
```

## Public vs. Private: Quick Reference

| Use `public/` for | Use `private/` for |
| --- | --- |
| Text formatting | Database reads / writes |
| Generic data transforms | File system operations |
| Unauthenticated API calls | Authenticated / secret API calls |
| App constants and metadata | Encryption and hashing |
| Input validation helpers | Credential management |
