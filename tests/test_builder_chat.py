"""Builder chat is advisory, not authoritative.

The builder agent can help an author think, but it must not silently
mutate pack files. The route is stateless, replay-limited, and returns
one proposed reply only.
"""

from fastapi.testclient import TestClient

from vefr import chat as chat_mod
from vefr.main import app


def test_builder_chat_returns_reply_without_mutating_pack(fixture_vefr_home, monkeypatch):
    notes = fixture_vefr_home / "worlds" / "four-phase-pack" / "lore-notes.md"
    assert not notes.exists()

    monkeypatch.setattr(chat_mod, "draft", lambda prompt, system=None: "proposal only")

    client = TestClient(app)
    r = client.post(
        "/api/builder/chat",
        json={
            "message": "Make the alley stranger, but not violent.",
            "history": [
                {"role": "user", "content": "The truck brings breakfast and news."},
                {"role": "assistant", "content": "Lean into warmth and scarcity."},
            ],
            "world": "four-phase-pack",
        },
    )

    assert r.status_code == 200
    assert r.json() == {"reply": "proposal only"}
    assert not notes.exists()

