from http import HTTPMethod
from unittest.mock import Mock

import pytest

from openpilot.tools.lib.github_utils import GithubUtils


@pytest.mark.parametrize("comments,marker,expected_path", [
  ([{"id": 1, "user": {"login": "bot"}, "body": "_model_tici_"},
    {"id": 2, "user": {"login": "bot"}, "body": "_model_chestnut_"}], "_model_chestnut_", "issues/comments/2"),
  ([{"id": 1, "user": {"login": "bot"}, "body": "_model_chestnut_"},
    {"id": 2, "user": {"login": "bot"}, "body": "_model_tici_"}], "_model_tici_", "issues/comments/2"),
  ([{"id": 1, "user": {"login": "other"}, "body": "_model_tici_"}], "_model_tici_", "issues/42/comments"),
  ([{"id": 1, "user": {"login": "bot"}, "body": "old report"}], "", "issues/comments/1"),
  ([], "_model_tici_", "issues/42/comments"),
])
def test_comment_overwrite_is_scoped_to_author_and_marker(comments, marker, expected_path):
  github = GithubUtils("", "")
  github.get_pr_number = Mock(return_value=42)
  github.api_call = Mock(return_value=Mock(json=Mock(return_value=comments)))

  github.comment_on_pr("new report", "branch", "bot", True, comment_marker=marker)

  calls = github.api_call.call_args_list
  assert calls[0].args == ("issues/42/comments",)
  assert calls[1].args == (expected_path,)
  assert calls[1].kwargs["method"] == (HTTPMethod.PATCH if expected_path.startswith("issues/comments/") else HTTPMethod.POST)
  assert calls[1].kwargs["data"] == '{"body": "new report"}'
  assert len(calls) == 2


def test_new_comment_does_not_read_or_replace_existing_comments():
  github = GithubUtils("", "")
  github.get_pr_number = Mock(return_value=42)
  github.api_call = Mock()

  github.comment_on_pr("new report", "branch", "bot", False, comment_marker="_model_tici_")

  github.api_call.assert_called_once_with("issues/42/comments", data='{"body": "new report"}', method=HTTPMethod.POST)
