from pathlib import Path
from types import SimpleNamespace
import subprocess

from openpilot.starpilot.software.history import commit_history, release_notes, recent_versions


def test_history_is_bounded_and_pinned_to_the_requested_commit(tmp_path):
  def git(*args):
    return subprocess.run(['git', '-C', str(tmp_path), '-c', 'core.hooksPath=/dev/null',
                           '-c', 'user.name=Test', '-c', 'user.email=test@example.com', *args],
                          check=True, capture_output=True, text=True).stdout.strip()
  git('init', '-q')
  for index in range(23):
    git('commit', '--allow-empty', '-qm', f'Change {index:02d}')
  commit = git('rev-parse', 'HEAD~1')
  rows = commit_history(tmp_path, commit)
  assert len(rows) == 20
  assert rows[0]['hash'] == commit and rows[0]['subject'] == 'Change 21'
  assert rows[-1]['subject'] == 'Change 02'
  assert all(row['date'] for row in rows)
  assert commit_history(tmp_path, '--all') == []
  assert commit_history(tmp_path, 'f' * 40) == []
  assert recent_versions(tmp_path, 'Dom')['entries'] == []
  git('update-ref', 'refs/starpilot/recent/Dom', commit)
  recent = recent_versions(tmp_path, 'Dom')
  assert recent['head'] == commit and recent['branch'] == 'Dom' and recent['entries'] == rows
  assert recent_versions(tmp_path, '../escape')['entries'] == []
  assert recent_versions(tmp_path, 'Dom')['entries'][0]['hash'] == commit


def test_release_notes_are_bounded_plain_text(tmp_path):
  params = SimpleNamespace(get_param_path=lambda key: str(tmp_path / key))
  path = Path(params.get_param_path('UpdaterCurrentReleaseNotes'))
  assert release_notes(params, path.name) is None
  path.write_text('<h1>StarPilot</h1><ul><li>First &amp; second</li></ul><script>danger()</script><style>.bad{}</style>')
  assert release_notes(params, path.name) == 'StarPilot\n\nFirst & second'
  path.write_bytes(b'x' * 32769)
  assert release_notes(params, path.name) is None
  path.write_bytes(b'\xff')
  assert release_notes(params, path.name) is None
