#!/usr/bin/env python3
"""Read-only source/manifest gate for the isolated native-artifact branch."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path.cwd().resolve()
output = Path(sys.argv[1]).resolve()
output.mkdir(parents=True, exist_ok=False)
manifest = json.loads(Path(__file__).with_name('frozen-source.json').read_text())

def git(*args):
  return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', *args], cwd=root)

def digest(raw):
  return hashlib.sha256(raw).hexdigest()

head = git('rev-parse', 'HEAD').decode().strip()
assert head == os.environ['GITHUB_SHA'], 'checkout is not the exact event commit'
assert os.environ['GITHUB_REF'] == 'refs/heads/' + manifest['expected_branch']
assert os.environ['GITHUB_REPOSITORY'] == 'firestar5683/StarPilot'
base = manifest['parent_commit']
git('cat-file', '-e', base + '^{commit}')
changed = git('diff', '--name-only', base, head).decode().splitlines()
source_paths = {row['path'] for row in manifest['source_whitelist']}
allowed = lambda p: p in source_paths or p == '.github/workflows/card_stall_native_artifact.yaml' or p.startswith('tools/ci/card_stall_native_artifact/')
assert all(allowed(p) for p in changed), changed
assert source_paths <= set(changed)
rows = []
for entry in manifest['source_whitelist']:
  path = entry['path']
  data = (root / path).read_bytes()
  assert digest(data) == entry['sha256'], path
  tree = git('ls-tree', head, '--', path).decode().strip().split()
  assert tree[0] == entry['git_mode'], (path, tree)
  assert digest(git('show', head + ':' + path)) == entry['sha256']
  rows.append({'path': path, 'sha256': digest(data), 'git_mode': tree[0], 'git_blob': tree[2]})
for key in ('baseline_native', 'baseline_companion'):
  entry = manifest[key]
  data = git('show', base + ':' + entry['path'])
  tree = git('ls-tree', base, '--', entry['path']).decode().strip().split()
  assert tree[0] == entry['git_mode'] and tree[2] == entry['git_blob']
  assert digest(data) == entry['sha256']
  assert (root / entry['path']).read_bytes() == data, 'unexpected already-replaced native artifact'
  (output / ('baseline-ipc_pyx.so' if key == 'baseline_native' else 'baseline-visionipc_pyx.so')).write_bytes(data)
assert not (root / 'openpilot/selfdrive/modeld/models').exists(), 'model payload checkout is outside this job'
source_tree = git('ls-tree', '-rz', '--full-tree', head)
(output / 'source-tree.git.bin').write_bytes(source_tree)
report = {'head': head, 'base': base, 'tree': git('rev-parse', 'HEAD^{tree}').decode().strip(),
          'changed_paths': changed, 'source_tree_sha256': digest(source_tree), 'frozen_sources': rows,
          'baseline_native': manifest['baseline_native'], 'baseline_companion': manifest['baseline_companion'],
          'workflow': '.github/workflows/card_stall_native_artifact.yaml', 'source_only_sparse_checkout': True}
(output / 'source.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
