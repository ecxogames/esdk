# Private Python Modules

Use `private/` for work involving protected data or computer resources.

Good uses:

- Reading and writing files
- Database access
- Passwords, tokens, and API keys
- Authenticated API calls
- Encryption and system operations

Example:

```python
# private/notes.py
def save_note(text):
    with open("note.txt", "w", encoding="utf-8") as file:
        file.write(text)
    return True
```

Call it only through a controlled server action:

```python
from private import notes

if action == "save_note":
    notes.save_note(request.get("text", ""))
    return json.dumps({"status": "ok"})
```

The folder is an organization rule, not a security sandbox. Validate frontend input and never return passwords, tokens, or unnecessary private data.
