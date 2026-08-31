"""The world wiki endpoint - canon voices joined to what they said."""

from vefr import journal


def test_api_wiki_joins_voices_to_lines(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    from vefr.main import app

    c = TestClient(app)
    # The sample world's first speaker, spoken to once.
    from vefr.world import load_world

    first = list(load_world()["speakers"].values())[0]["name"]
    journal.log("npc_line", sid="wiki1", phase="whispers", speaker=first, line="hello")
    journal.log("npc_line", sid="wiki1", phase="whispers", speaker="A Stranger", line="who?")

    body = c.get("/api/wiki", params={"session": "wiki1"}).json()
    names = {ch["name"]: ch for ch in body["characters"]}
    # The canon voice shows zero lines this session; the stranger
    # shows up with theirs.
    assert names[first]["lines"] == 0
    assert names["A Stranger"]["lines"] == 1
    assert names["A Stranger"]["recent"][0]["line"] == "who?"
    assert body["rumors"] == 0
    assert body["relics"] == []
