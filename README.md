# Landmark-Based Episodic Memory Assistance

Privacy-preserving three-component implementation:

1. `edge_device/` — perception and semantic-memory storage.
2. `server/` — retrieves semantic data, calls Gemini, and exposes the web API.
3. `website/` — browser UI only; it never receives the Gemini API key or camera data.

## Privacy boundary

The intended production flow is:

Camera/perception -> semantic events -> edge database
                                      |
                                      v
                                  server
                                      |
                              relevant records
                                      |
                                      v
                                  Gemini API
                                      |
                                      v
                                  website

Raw images/video are not part of the server/Gemini interface.

## Prototype mode

The edge component includes a small Python SQLite implementation so the complete system can be tested on a normal PC before moving the database/device interface to an ESP32-class device.

The server can operate in:
- `local` mode: read a local SQLite database (development only)
- `http` mode: request semantic records from an edge HTTP endpoint (recommended architecture)

## Quick start

### 1. Server

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Put GEMINI_API_KEY in .env
python -m app.app
```

Open `website/index.html` through a static server, or configure the website API URL to the server.

For the easiest local demo, from the project root:

```powershell
cd website
python -m http.server 8080
```

Then open `http://127.0.0.1:8080`.

### 2. Seed/test edge database

```powershell
cd edge_device
python src/demo_seed.py
```

Then configure the server for local mode.

## GitHub

Do not commit `.env`, API keys, private databases, camera recordings, or generated artifacts. The supplied `.gitignore` protects these by default.
