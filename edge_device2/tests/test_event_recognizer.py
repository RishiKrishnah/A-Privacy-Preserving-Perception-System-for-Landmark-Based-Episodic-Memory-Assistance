from types import SimpleNamespace
from src.events.event_recognizer import EventRecognizer


def det(label, tid, cx, cy, conf=0.9, size=40):
    return SimpleNamespace(
        label=label, track_id=tid, confidence=conf,
        center=(cx,cy),
        xyxy=(int(cx-size/2),int(cy-size/2),int(cx+size/2),int(cy+size/2)),
    )


def hand(cx, cy, conf=0.95):
    return SimpleNamespace(center=(cx,cy), confidence=conf)


def test_pick_requires_sustained_contact_and_motion():
    r = EventRecognizer(
        ["wallet"], ["table"],
        contact_distance_px=80, movement_distance_px=10,
        min_moving_frames=2, contact_frames=2,
        release_frames=2, stable_frames=2, cooldown_seconds=0,
    )

    assert r.update([det("wallet",1,100,100)],[hand(100,100)],[]) == []
    assert r.update([det("wallet",1,108,100)],[hand(108,100)],[]) == []
    events = r.update([det("wallet",1,125,100)],[hand(125,100)],[])
    assert any(e.action == "PICK" for e in events)


def test_place_contains_landmark():
    r = EventRecognizer(
        ["wallet"], ["table"],
        contact_distance_px=80, movement_distance_px=10,
        min_moving_frames=1, contact_frames=1,
        release_frames=2, stable_frames=2, cooldown_seconds=0,
    )

    r.update([det("wallet",1,100,100)],[hand(100,100)],{})
    r.update([det("wallet",1,120,100)],[hand(120,100)],{})

    lm = SimpleNamespace(label="table", confidence=0.9)
    r.update([det("wallet",1,160,100)],[],{1:lm})
    r.update([det("wallet",1,160,100)],[],{1:lm})
    events = r.update([det("wallet",1,160,100)],[],{1:lm})

    assert any(e.action == "PLACE" and e.landmark == "table" for e in events)
