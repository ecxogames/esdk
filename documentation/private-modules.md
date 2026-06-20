# Private Modules

The `private/` directory is for Python code that performs sensitive operations. Functions here are only reachable through the server layer — the JavaScript frontend has no direct access to them, and they are never exposed as importable modules from the UI side.

## What Belongs in `private/`

- Database reads and writes (SQLite, PostgreSQL, etc.)
- File system operations (reading/writing user data files)
- Cryptographic operations (hashing, encryption, signing)
- Calls to authenticated or paid external APIs (API keys live here)
- Credential and token management
- Any logic that must not be visible or inspectable from the frontend

If a function is purely a helper with no sensitive data access, put it in [`public/`](public-modules.md) instead. Keep `private/` for operations where exposure would be a security risk.

## File Structure

```
private/
└── secret_processor.py   ← default sensitive operations module
```

Add additional files as your application grows (e.g. `private/database.py`, `private/auth.py`). Each file is imported as `from private import database` etc.

## The Default Module: `secret_processor.py`

The template ships with `private/secret_processor.py` containing a demonstration of a secure backend operation:

```python
# private/secret_processor.py
import hashlib
import os

def process_secure_data(data):
    if not data:
        return "No data provided."

    encrypted = hashlib.sha256(data.encode('utf-8')).hexdigest()

    # Example: write to a local database
    # db.execute("INSERT INTO secret_table (data_hash) VALUES (?)", encrypted)

    return f"Private Layer successfully secured the data. SHA-256 Hash: {encrypted[:15]}..."
```

This function hashes the input string with SHA-256 — a stand-in for any real cryptographic or database operation. The raw input never leaves the Python layer; the UI only receives a confirmation message and a truncated hash.

## Importing Private Modules in the Server

Import at the top of `server/api.py` and call inside the relevant action handler:

```python
from private import secret_processor

def handle_message(message_str):
    ...
    elif action == "private_demo":
        result = secret_processor.process_secure_data(req.get("secret_data", ""))
        return json.dumps({"status": "ok", "result": result})
```

Only ever import private modules inside `server/api.py` (or other server-side files). Never import them from `public/` or from the UI layer.

## Adding a New Private Function

**Step 1** — Add the function to an existing or new file inside `private/`:

```python
# private/database.py
import sqlite3

DB_PATH = "data/app.db"

def save_user_note(user_id, note_text):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO notes (user_id, body) VALUES (?, ?)",
        (user_id, note_text)
    )
    con.commit()
    con.close()
    return "Note saved."
```

**Step 2** — Import the new file and add an action handler in `server/api.py`:

```python
from private import database

elif action == "save_note":
    result = database.save_user_note(
        req.get("user_id"),
        req.get("note")
    )
    return json.dumps({"status": "ok", "result": result})
```

**Step 3** — Call it from JavaScript:

```javascript
window.invokeBridge({ action: "save_note", user_id: 1, note: "Buy milk" })
    .then(res => console.log(res.result)); // "Note saved."
```

The database file, SQL queries, and user IDs never touch the JavaScript layer. The frontend only sees the string returned by `json.dumps`.

## Security Model

The separation between `public/` and `private/` is enforced by convention, not by a sandbox. The guarantee comes from the architecture:

- JavaScript can only trigger actions that are explicitly handled in `server/api.py`.
- The server layer controls exactly what data is returned to the UI — it never forwards raw database rows, file contents, or secret values unless you explicitly do so.
- Private modules are never imported by UI code or public modules, so their internals stay opaque to the frontend.

When in doubt, return only what the UI strictly needs. For example, instead of returning a full database row, return only the fields the view requires, or a simple success/failure message.
