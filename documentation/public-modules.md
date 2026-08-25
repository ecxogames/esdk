# Public Python Modules

Use `public/` for reusable Python code that does not use secrets or protected resources.

Good uses:

- Formatting and calculations
- Input validation
- Data sorting and filtering
- Public API calls without credentials

Example:

```python
# public/prices.py
def format_price(value):
    return f"${value:,.2f}"
```

Expose it through `server/api.py`:

```python
from public import prices

if action == "format_price":
    result = prices.format_price(request.get("value", 0))
    return json.dumps({"status": "ok", "result": result})
```

`public` does not mean browser-accessible. It is still Python backend code. JavaScript can only reach actions you add to `server/api.py`.
