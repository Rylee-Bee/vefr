# Test Templates

Copy-paste starting points for testing vefr's storytelling boundaries.

## Running Tests

```bash
# All tests (fast, no model required)
uv run --group test pytest -q

# One file, verbose
uv run --group test pytest tests/templates/test_storyteller_contract.py -v

# Lint gate
uv run --group test ruff check src tests
```

## How to Copy a Template

1. Pick the template closest to your need.
2. Copy the file into `tests/` (or wherever your test lives).
3. Rename it. Replace the canned responses with your scenario.
4. Run it. It should pass green before you change anything else.

Templates are deliberately minimal. Strip what you don't need.

## What Each Template Protects

| Template | Invariant |
|---|---|
| `test_storyteller_contract.py` | The storyteller renders the world. It does not own the world. |
| `test_canon_boundary.py` | Characters cannot learn facts the world has sealed. |
| `test_continuity_example.py` | State persists across turns. Memory is not optional. |
| `test_storyteller_provider.py` | Provider failures degrade gracefully, never silently. |
| `test_player_agency.py` | The model narrates the world, not the player's choices. |

## Fast Tests vs Model Qualification Tests

**Fast tests** (these templates) monkeypatch `generator._completion`
with canned responses. No model is loaded. No network call is made.
They run in milliseconds and prove the *boundary logic* is correct.

**Model qualification tests** (the audition harness in
`test_storyteller_test.py`) hit a real model. They prove the *model*
can hold a scene. They are slower, flakier, and SKIPPED when the
model is not installed.

Write fast tests first. Prove the contract. Then audition models
against the contract.

## Fixtures

Golden JSON fixtures live in `fixtures/`. Each one is a complete
`ScenePacket`-shaped object ready for `SceneFixture(**data)`.

Load them with:

```python
from vefr.storyteller_test import load_fixture
scene = load_fixture("two_distinct_characters")
packet = scene.to_packet()
```
