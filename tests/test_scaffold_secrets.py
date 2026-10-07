"""Secrets never reach the terminal or the new repo's config.

Two shapes of leak, one per function:

* `sh()` echoes every command it runs. A remote URL carrying a
  password went to stdout in clear text (CodeQL
  py/clear-text-logging-sensitive-data), so the echo now redacts the
  userinfo while the command that actually runs is untouched.
* `cmd_scaffold --push` read this checkout's origin credentials,
  called the Gitea API with them, and wrote a `user:token@host` URL
  into the new repo's .git/config. It now never touches credentials
  and prints the by-hand push instead.

Pure python, no network, no forge. The credentials below are obvious
placeholders, not secrets.
"""

import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from vefr import cli

# Obviously fake. These strings exist to be recognized, never to be used.
PLACEHOLDER_TOKEN = 'EXAMPLE-TOKEN-NOT-A-SECRET'


def _stub_run(cmd, **kw):
    """Stand in for subprocess.run: nothing is executed, and the argv is
    what the assertion looks at. Printing is the only thing under test,
    so no real git, no network, no working tree touched."""
    return subprocess.CompletedProcess(cmd, 0, '', '')


class ShRedactionTests(unittest.TestCase):
    """sh() prints the shape of a command, not its credentials."""

    def _printed(self, *cmd):
        out = io.StringIO()
        with mock.patch.object(subprocess, 'run', side_effect=_stub_run) as run:
            with contextlib.redirect_stdout(out):
                cli.sh(cmd)
        return out.getvalue().strip(), run

    def test_user_and_password_at_host_is_redacted(self):
        printed, run = self._printed(
            'git', '-C', '/tmp/out', 'remote', 'add', 'origin',
            f'https://scripter:{PLACEHOLDER_TOKEN}@forge.example/owner/name.git',
        )
        self.assertNotIn(PLACEHOLDER_TOKEN, printed)
        self.assertIn(
            'https://scripter:***@forge.example/owner/name.git', printed)
        # The command that ran kept the real argument - only the echo
        # is redacted, so `sh` still does its job.
        self.assertIn(PLACEHOLDER_TOKEN, ' '.join(run.call_args.args[0]))

    def test_token_only_userinfo_is_fully_redacted(self):
        printed, _ = self._printed(
            'git', 'remote', 'set-url', 'origin',
            f'https://{PLACEHOLDER_TOKEN}@forge.example/owner/name.git',
        )
        self.assertNotIn(PLACEHOLDER_TOKEN, printed)
        self.assertIn('https://***@forge.example/owner/name.git', printed)

    def test_url_without_userinfo_is_printed_as_is(self):
        url = 'https://forge.example/owner/name.git'
        printed, _ = self._printed('git', 'clone', url)
        self.assertEqual(f'+ git clone {url}', printed)

    def test_command_without_a_url_is_printed_as_is(self):
        printed, _ = self._printed('git', '-C', '/tmp/out', 'status', '-sb')
        self.assertEqual('+ git -C /tmp/out status -sb', printed)

    def test_scp_style_remote_is_untouched(self):
        """`git@host:path` has no scheme, so it is not a URL with
        userinfo - an SSH key lives in ~/.ssh, not in the string."""
        printed, _ = self._printed('git', 'clone', 'git@forge.example:o/n.git')
        self.assertEqual('+ git clone git@forge.example:o/n.git', printed)


class ScaffoldPushTests(unittest.TestCase):
    """cmd_scaffold leaves the push to the author, credentials and all
    network calls out of the process."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        pack = self.root / 'worlds' / 'pack'
        pack.mkdir(parents=True)
        (pack / 'world.json').write_text('{"title": "T"}', encoding='utf-8')
        (pack / 'logbok.md').write_text('# canon', encoding='utf-8')
        self.dest = self.root / 'out'
        patches = (
            mock.patch.object(cli, 'pack_root', return_value=self.root),
            mock.patch.object(cli, 'world_name', return_value='pack'),
        )
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _args(self, push=True):
        return type('A', (), {'dest': str(self.dest), 'name': 'pack',
                              'push': push})()

    def test_scaffold_never_calls_urllib(self):
        def no_network(*a, **kw):  # pragma: no cover - must not run
            raise AssertionError('scaffold opened a network connection')

        out = io.StringIO()
        with mock.patch('urllib.request.urlopen', side_effect=no_network), \
                mock.patch.object(cli, 'need_repo', side_effect=no_network):
            with contextlib.redirect_stdout(out):
                rc = cli.cmd_scaffold(self._args())
        self.assertEqual(0, rc)

    def test_scaffold_writes_no_credentials_and_no_remote(self):
        out = io.StringIO()
        with mock.patch('urllib.request.urlopen',
                        side_effect=AssertionError('network')), \
                mock.patch.object(cli, 'need_repo',
                                  side_effect=AssertionError('network')):
            with contextlib.redirect_stdout(out):
                self.assertEqual(0, cli.cmd_scaffold(self._args()))

        config = (self.dest / '.git' / 'config').read_text(encoding='utf-8')
        self.assertNotIn('[remote ', config)
        self.assertNotIn(PLACEHOLDER_TOKEN, config)
        # Nothing anywhere in the exported repo reads like a secret.
        for path in self.dest.rglob('*'):
            if path.is_file():
                self.assertNotIn(PLACEHOLDER_TOKEN,
                                 path.read_text(encoding='utf-8',
                                                errors='replace'))

        # And the author is told how to push, with no secret in the text.
        printed = out.getvalue()
        self.assertIn(f'git -C {self.dest} remote add origin <your repo url>',
                      printed)
        self.assertIn('push -u origin main', printed)

    def test_scaffold_push_flag_does_not_change_the_outcome(self):
        """--push stays accepted so old invocations keep working; it no
        longer reaches for a forge."""
        with mock.patch('urllib.request.urlopen',
                        side_effect=AssertionError('network')):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, cli.cmd_scaffold(self._args(push=True)))
        config = (self.dest / '.git' / 'config').read_text(encoding='utf-8')
        self.assertNotIn('[remote ', config)

    def test_no_credential_is_ever_built_into_a_shell_command(self):
        """The commands sh() ran carry no userinfo at all, so nothing
        with a password can reach a log through the echo either."""
        seen = []

        def record(cmd, **kw):
            seen.append([str(c) for c in cmd])
            return subprocess.CompletedProcess(cmd, 0, '', '')

        with mock.patch.object(subprocess, 'run', side_effect=record):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, cli.cmd_scaffold(self._args()))
        for argv in seen:
            for arg in argv:
                self.assertNotIn('@forge.example', arg)


if __name__ == '__main__':
    unittest.main()