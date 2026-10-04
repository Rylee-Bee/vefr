#!/usr/bin/env python3
"""cut.py: one front door to the art cutters, picked by role.

  uv run --with pillow python tools/art/cut.py ROLE ARGS...

ROLE is one of:
  item-icon, creature   process_sprites.py
  tile                  process_tiles.py
  ui-part               process_ui.py

Everything after ROLE is forwarded to the chosen tool's main(argv). Needs Pillow.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import process_sprites
import process_tiles
import process_ui

ROLES = {
    "item-icon": process_sprites,
    "creature": process_sprites,
    "tile": process_tiles,
    "ui-part": process_ui,
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ROLES:
        print("usage: cut.py ROLE ARGS... (ROLE is item-icon, creature, tile or ui-part)",
              file=sys.stderr)
        return 2
    return ROLES[argv[0]].main(argv[1:])


if __name__ == "__main__":
    sys.exit(main())
