"""VEFR_DATA_DIR moves every piece of runtime state, so a test copy never writes the real one."""
import os
import subprocess
import sys


def test_every_runtime_file_follows_vefr_data_dir(tmp_path):
    code = r'''
import json
from vefr import paths, journal, forge, trace, sessions, teach, interface, narrate, lore_shell
from vefr import weave
out = {
  "data_dir": str(paths.data_dir()),
  "journal": str(journal.JOURNAL) if hasattr(journal, "JOURNAL") else "",
  "vault": str(forge.VAULT),
  "trace": str(trace._path()) if hasattr(trace, "_path") else "",
  "learning": str(teach._store()),
  "active": str(paths.active_world_file()),
}
print(json.dumps(out))
'''
    env = {**os.environ, "VEFR_DATA_DIR": str(tmp_path)}
    env.pop("VEFR_JOURNAL", None)
    env.pop("VEFR_VAULT", None)
    r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    import json
    got = json.loads(r.stdout.strip().splitlines()[-1])
    for key, path in got.items():
        if path:
            assert path.startswith(str(tmp_path)), f"{key} ignores VEFR_DATA_DIR: {path}"
