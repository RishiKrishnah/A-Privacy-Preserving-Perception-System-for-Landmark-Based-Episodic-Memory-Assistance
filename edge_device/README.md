# Edge Device

This component is responsible for producing and storing semantic episodic memories.

Production responsibility:
- camera/perception runs here
- convert observations to semantic events
- store semantic records
- expose only semantic records to the server

The included Python code is a hardware-neutral reference implementation. It is intentionally separated from the server so the perception implementation can later be replaced by ESP32/ESP32-S3 firmware or another edge computer.

## Database

The prototype database is `data/memory.db`.

Example record:

```json
{
  "timestamp": "2026-09-03T18:32:25",
  "subject": "wallet",
  "action": "PLACE",
  "landmark": "shelf"
}
```

No image/video column is required.

## Edge HTTP interface

`src/edge_api.py` provides a reference semantic-data HTTP service:

- `GET /health`
- `GET /memory/recent?limit=20`
- `GET /memory/search?q=wallet&limit=20`
- `GET /memory/events?from=...&to=...`

A constrained embedded device does not have to run this exact Python service. It defines the contract that an ESP32-class implementation can reproduce.
