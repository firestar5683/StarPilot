"""Report identity from the real caller, without inference, uploads or network."""
from unittest.mock import Mock

import pytest

from openpilot.selfdrive.test.process_replay import model_replay


@pytest.mark.parametrize('chestnut,model_type,title', [
  (False, 'tici', 'Small model'),
  (True, 'chestnut', 'Big model (Chestnut)'),
])
def test_actual_model_report_has_stable_marker_and_preserves_artifact_identity(monkeypatch, chestnut, model_type, title):
  branch, commit = 'report-regression', 'a' * 40
  github = Mock()
  github.get_pr_number.return_value = 42
  github.get_bucket_link.return_value = 'https://example.invalid/report'
  monkeypatch.setenv('GIT_BRANCH', branch)
  monkeypatch.setattr(model_replay, 'CHESTNUT', chestnut)
  monkeypatch.setattr(model_replay, 'GITHUB', github)
  monkeypatch.setattr(model_replay, 'get_commit', lambda: commit)
  report = Mock(return_value=[('changed.png', False), ('same.png', True)])
  save = Mock()
  monkeypatch.setattr(model_replay, 'generate_report', report)
  monkeypatch.setattr(model_replay, 'save_log', save)
  proposed, master, full_logs = [object()], [object()], [object()]

  model_replay.comment_replay_report(proposed, master, full_logs)

  report.assert_called_once()
  assert report.call_args.args[:2] == (proposed, master)
  assert report.call_args.args[3] == commit
  bucket = f'model_replay_{branch}_{model_type}'
  assert github.upload_files.call_args.args[0] == bucket
  expected_log = model_replay.get_log_fn(model_replay.TEST_ROUTE, commit)
  save.assert_called_once_with(expected_log, full_logs)
  github.upload_file.assert_called_once_with(bucket, expected_log, expected_log)
  github.comment_on_pr.assert_called_once()
  body, posted_branch, author, overwrite = github.comment_on_pr.call_args.args
  marker = github.comment_on_pr.call_args.kwargs['comment_marker']
  assert marker == f'_model_{model_type}_'
  assert marker in body
  assert f'<h2>Model Replay: {title}</h2>' in body
  assert f'https://example.invalid/report/{expected_log}' in body
  assert 'Model Replay Differences' in body and 'All Model Replay Plots' in body
  assert (posted_branch, author, overwrite) == (branch, 'commaci-public', True)
