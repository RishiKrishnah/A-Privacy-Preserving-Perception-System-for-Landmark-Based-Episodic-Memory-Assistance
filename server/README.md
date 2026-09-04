# Server

The server is the trusted application layer between the website, edge device and Gemini.

Responsibilities:
1. receive the user's natural-language question
2. retrieve only relevant semantic memories
3. construct a grounded Gemini request
4. return the answer to the website

The Gemini API key stays on the server.

## Configuration

Copy `.env.example` to `.env` and set:

```text
GEMINI_API_KEY=...
EDGE_MODE=local
LOCAL_DB_PATH=../edge_device/data/memory.db
```

For the eventual edge device:

```text
EDGE_MODE=http
EDGE_BASE_URL=http://EDGE_DEVICE_IP:9000
```

In `http` mode the server never opens the edge SQLite file. It calls the edge semantic-memory HTTP contract.

## API

- `GET /api/health`
- `GET /api/memories/recent`
- `POST /api/query`

Example query:

```json
{"question": "Where did I leave my wallet?"}
```
