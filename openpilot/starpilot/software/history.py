"""Bounded local history and plain-text notes from the existing updater."""

from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess

from openpilot.starpilot.saved_source import read_saved

COMMIT = re.compile(r'[0-9a-f]{40}\Z')
MAX_COMMITS = 20
MAX_NOTES_BYTES = 32768


def commit_history(path: Path, commit: str) -> list[dict]:
  if not COMMIT.fullmatch(commit):
    return []
  try:
    output = subprocess.run(
      ['git', '-C', str(path), '--no-pager', 'log', '--no-decorate', '--no-color', '--no-show-signature',
       f'-{MAX_COMMITS}', '--format=%H%x00%cI%x00%<(240,trunc)%s%x00', commit, '--'],
      check=True, capture_output=True, text=True, timeout=2).stdout
    if len(output.encode()) > 32768:
      return []
    fields = output.split('\0')
    rows = []
    for index in range(0, len(fields) - 2, 3):
      sha, date, subject = fields[index].strip(), fields[index + 1], fields[index + 2].rstrip()
      if not COMMIT.fullmatch(sha) or len(subject) > 500:
        return []
      parsed = datetime.fromisoformat(date)
      if parsed.tzinfo is None:
        return []
      rows.append({'hash': sha, 'date': parsed.isoformat(), 'subject': ''.join(c for c in subject if c.isprintable())})
    return rows[:MAX_COMMITS]
  except (OSError, ValueError, subprocess.SubprocessError):
    return []


class _NotesText(HTMLParser):
  def __init__(self):
    super().__init__(convert_charrefs=True)
    self.parts = []
    self.hidden = 0

  def handle_starttag(self, tag, attrs):
    if tag in ('script', 'style'):
      self.hidden += 1
    elif not self.hidden and tag in ('br', 'p', 'li', 'h1', 'h2', 'h3'):
      self.parts.append('\n')

  def handle_endtag(self, tag):
    if tag in ('script', 'style'):
      self.hidden = max(0, self.hidden - 1)
    elif not self.hidden and tag in ('p', 'li', 'h1', 'h2', 'h3'):
      self.parts.append('\n')

  def handle_data(self, data):
    if not self.hidden:
      self.parts.append(data)


def release_notes(params, key: str) -> str | None:
  raw, readable = read_saved(params, key, MAX_NOTES_BYTES)
  if not readable or raw is None:
    return None
  try:
    parser = _NotesText()
    parser.feed(raw.decode('utf-8'))
    parser.close()
    return re.sub(r'\n{3,}', '\n\n', ''.join(parser.parts)).strip()
  except (UnicodeError, ValueError):
    return None
