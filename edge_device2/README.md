# Robust `edge_device1`

This is a replacement for the currently used `edge_device1/` folder. The old
`edge_device/` folder is not required.

## Main improvement

The previous recognizer treated almost every non-person detection as an
object and inferred PICK/PLACE mainly from movement and proximity to a person.
It also did not populate the landmark field.

This version explicitly separates:

- personal objects
- landmarks (`table`, `desk`, `shelf`, `bed`, `cupboard`)
- person
- hands

and uses a temporal state machine.

```text
Webcam
  ↓
YOLO-World rich prompts
  ↓
personal objects + landmarks
  ↓
MediaPipe hand tracking
  ↓
temporal PICK / MOVE / PLACE
  ↓
temporal landmark association
  ↓
confidence filtering
  ↓
semantic deduplication
  ↓
SQLite
```

## Why table/desk detection is improved

YOLO-World receives richer prompts:

```text
table, tabletop, dining table, desk table
desk, office desk, study desk, work desk
shelf, shelving, bookshelf
cupboard, cabinet, wardrobe
```

The detector converts these back into canonical labels, so memory still uses
simple labels such as `table` and `desk`.

Landmarks also use a lower detection threshold than personal objects. This is
intentional because furniture can be partially visible.

## Event logic

### PICK

Requires:

1. hand close to the object for multiple frames
2. object movement for multiple frames

### MOVE

Optional and emitted only after a confirmed PICK.

### PLACE

Requires:

1. previous PICK
2. hand release
3. object stability
4. a temporally confirmed landmark

So simply seeing a stationary wallet does not create a PLACE event.

## Install

From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If your existing environment already works:

```powershell
pip install -r requirements.txt
```

YOLO-World weights are loaded through Ultralytics. If the configured model is
not local, Ultralytics normally downloads it.

The MediaPipe hand model is downloaded automatically to:

```text
data/hand_landmarker.task
```

No video/image is written to disk.

## Run

From inside `edge_device1`:

```powershell
python -m src.main
```

Camera override:

```powershell
python -m src.main --camera 1
```

No preview:

```powershell
python -m src.main --no-window
```

Press `Q` to stop.

## Run API

In another terminal:

```powershell
python -m src.edge_api
```

The default API is:

```text
http://127.0.0.1:9000
```

Endpoints:

```text
GET /health
GET /memory/recent
GET /memory/search?q=wallet
GET /memory/events
```

The server-side API contract remains semantic-only.

## Inspect memory

```powershell
python -m src.inspect_memory
```

## Test

Install pytest if needed:

```powershell
pip install pytest
```

Then:

```powershell
pytest -q
```

## Recommended live test

First test furniture recognition alone:

1. Put a clearly visible table or desk in the webcam view.
2. Keep it visible for several seconds.
3. Confirm the preview repeatedly shows `table` or `desk`.
4. Only then test object interaction.

For a placement test:

```text
wallet on table
      ↓
hand touches wallet
      ↓
wallet is moved
      ↓
hand releases wallet
      ↓
wallet remains stable
      ↓
PLACE(wallet, table)
```

Expected semantic memory:

```text
wallet | PICK  | -
wallet | MOVE  | -
wallet | PLACE | table
```

The exact result depends on camera angle, lighting, object visibility and model
confidence.

## Tuning

If furniture is still missed, try only:

```yaml
perception:
  landmark_confidence: 0.15
```

If PICK is too difficult:

```yaml
events:
  contact_distance_px: 125
  movement_distance_px: 12
  contact_frames: 2
```

If false PICK events occur, increase the contact/movement requirements.

If PLACE is too difficult:

```yaml
events:
  landmark_max_gap_px: 220
  landmark_confirmations: 2
```

Change one parameter at a time.

## Privacy

Only semantic records are stored:

- timestamp
- subject
- action
- landmark
- confidence
- details

Raw frames are processed in memory and are never stored or returned by the
edge API.

## Important

Do not copy the old `edge_device/` code into this folder. This ZIP is intended
to replace the contents of your currently used `edge_device1/`.
