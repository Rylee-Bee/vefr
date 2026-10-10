"""Build the story-status fixture packs (vefr #339).

Two neutral engine-test packs, both sample-world with a `library/` and
a `status` key written onto words that are about nothing but the
contract:

- `status-test`     - nothing is a draft: every book is approved or
                      carries no key at all, and one of each record kind
                      on the JSON side is marked `approved`.
- `status-drafts`   - one draft word of every kind (book, voice file,
                      speaker voice file, say rule, sticker, item), plus
                      a `status` written as neither `draft` nor
                      `approved` so the refusal has something to say.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"

BOOKS = {
    # no key at all: the pack that predates the feature, unchanged
    "a-shelf-book": "---\ntitle: A Shelf Book\n---\nThe first page.\n",
    "an-approved-book": "---\ntitle: An Approved Book\nstatus: approved\n---\nRead me.\n",
}

# The one book that is a draft. The draft pack carries all three, so
# "lists exactly the draft one" is a claim about the other two too.
DRAFT_BOOK = ("a-draft-book",
              "---\ntitle: A Draft Book\nstatus: draft\nkind: note\n---\nNot canon yet.\n")

# The record kinds the JSON surfaces carry, each with the status the
# named pack gives it.
RECORDS = {
    "approved": {
        "items": {"pitch-torch": {"name": "a pitch torch"}},
        "voices": {"keeper": {"file": "voices/keeper.md", "strike": "Strike."}},
        "album": [{"id": "first-stamp", "name": "A First Stamp",
                   "kind": "open", "when": {"starts": {}}}],
        "rules": [{"id": "keeper-greet",
                   "when": {"enters": {"place": "town"}},
                   "then": [{"say": "Sit. The stone does not ask."}]}],
    },
    "drafts": {
        "items": {"draft-torch": {"name": "a torch that is not canon",
                                  "status": "draft"}},
        "voices": {"draft-keeper": {"file": "voices/keeper.md",
                                    "strike": "Write it.",
                                    "status": "draft"}},
        "album": [{"id": "draft-stamp", "name": "A Stamp Not Canon",
                   "kind": "open", "when": {"starts": {}},
                   "status": "draft"}],
        "rules": [{"id": "draft-greet",
                   "when": {"enters": {"place": "town"}},
                   "status": "draft",
                   "then": [{"say": "Words no one has read yet."}]}],
    },
}


def _write_record(world_path: Path, block: dict) -> None:
    data = json.loads(world_path.read_text(encoding="utf-8"))
    for key, value in block.items():
        data[key] = value if key != "items" else {**data.get("items", {}), **value}
    world_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def build(dest: Path, drafts: bool = False) -> Path:
    """The story-status fixture pack, at `dest/worlds/<name>`."""
    name = "status-drafts" if drafts else "status-test"
    pack = dest / "worlds" / name
    if pack.exists():
        shutil.rmtree(pack)
    pack.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE, pack)
    lib = pack / "library"
    if lib.exists():
        shutil.rmtree(lib)
    lib.mkdir()
    for stem, text in BOOKS.items():
        (lib / f"{stem}.md").write_text(text, encoding="utf-8")
    if drafts:
        (lib / f"{DRAFT_BOOK[0]}.md").write_text(DRAFT_BOOK[1], encoding="utf-8")
    _write_record(pack / "world.json", RECORDS["drafts" if drafts else "approved"])
    if drafts:
        # A speaker whose voice file is a draft: the second way a pack
        # names a voice file, and the one an acts-shape pack uses.
        data = json.loads((pack / "acts/act-1/world.json").read_text(encoding="utf-8"))
        data["speakers"]["keeper"]["status"] = "draft"
        (pack / "acts/act-1/world.json").write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return pack


def build_unknown(dest: Path) -> Path:
    """A pack whose one `status` is neither `draft` nor `approved`."""
    pack = build(dest, drafts=False)
    world = pack / "world.json"
    data = json.loads(world.read_text(encoding="utf-8"))
    data["items"]["confused-torch"] = {"name": "a torch", "status": "maybe"}
    world.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return pack


if __name__ == "__main__":
    print(str(build(Path(sys.argv[1]), drafts="--drafts" in sys.argv[2:])))