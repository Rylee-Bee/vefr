import json


from vefr import forge, generator
from vefr.forge import ItemCard, build_payload, forge_item, keep_item, list_vault


GOOD = json.dumps(
    {
        "name": "The Ledger-Ribbon",
        "kind": "ribbon",
        "bond": "attuned",
        "lore": "Tied once to a door that had forgotten how to open.",
    }
)


def test_payload_keeps_bond_structure():
    from vefr.world import load_world

    p = build_payload()
    assert p['format']['properties']['bond']['enum'] == list(
        load_world()['bonds'].keys()
    )
    assert 'rarity is the point' in p['prompt']


def test_forge_parses_item(monkeypatch):
    monkeypatch.setattr(generator, "_completion", lambda *a, **k: GOOD)
    item = forge_item()
    assert item.name == "The Ledger-Ribbon"
    assert item.bond == "attuned"


def test_vault_roundtrip(monkeypatch, tmp_path):
    vault_file = tmp_path / "vault.json"
    monkeypatch.setattr(forge, "VAULT", vault_file)
    assert list_vault() == []
    item = ItemCard.model_validate_json(GOOD)
    result = keep_item(item)
    assert result["kept"] is True and result["count"] == 1
    kept = list_vault()
    assert kept[0]["name"] == "The Ledger-Ribbon"
