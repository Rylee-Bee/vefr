import os
from pathlib import Path

# The pack resolves before any old-name import: the author's world when
# present, the demonstration world otherwise. The bones never require
# the flesh to prove themselves.
_pack = Path(__file__).resolve().parents[1] / 'worlds' / 'private-canon'
os.environ.setdefault(
    'SMIDR_WORLD',
    'private-canon' if (_pack / 'world.json').exists() else 'sample-world',
)
