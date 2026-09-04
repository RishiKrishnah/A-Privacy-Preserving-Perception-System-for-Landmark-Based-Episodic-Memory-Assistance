# Website

Static frontend. It communicates only with the server API.

It does not contain:
- Gemini credentials
- SQLite credentials
- camera access
- perception code

For development:

```powershell
cd website
python -m http.server 8080
```

Then open `http://127.0.0.1:8080`.
