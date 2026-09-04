# Testing checklist

## Furniture recognition

- Table/desk is clearly visible.
- Preview shows `table` or `desk` repeatedly.
- No event needs to be generated for a stationary landmark.

## PICK

- Hold a wallet/phone/bottle still.
- Put a hand next to/on it.
- Keep contact for several frames.
- Move it.
- Expect `PICK`.

## MOVE

- Continue moving after PICK.
- Expect optional `MOVE`.

## PLACE

- Move the object over a visible table/desk.
- Release the object.
- Keep it still for the required stable frames.
- Expect `PLACE -> table` or `PLACE -> desk`.

## Database

```powershell
python -m src.inspect_memory
```

## API

```powershell
python -m src.edge_api
```

Then open:

```text
http://127.0.0.1:9000/health
http://127.0.0.1:9000/memory/recent
```
