"""On-device layout for Spotify Soloist. Everything the feature owns lives under one root."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROOT = Path('/data/starpilot/soloist')
CONTROL_SOCKET = '/tmp/starpilot-spotify.sock'


@dataclass(frozen=True)
class Layout:
  root: Path

  @classmethod
  def default(cls) -> Layout:
    return cls(Path(os.environ.get('STARPILOT_SOLOIST_ROOT', DEFAULT_ROOT)))

  @property
  def releases(self) -> Path: return self.root / 'releases'
  @property
  def current(self) -> Path: return self.root / 'current'
  @property
  def previous(self) -> Path: return self.root / 'previous'
  @property
  def config(self) -> Path: return self.root / 'config.json'
  @property
  def enabled_flag(self) -> Path: return self.root / 'enabled'
  @property
  def api_key(self) -> Path: return self.root / 'secrets' / 'api_key'
  @property
  def state(self) -> Path: return self.root / 'state'
  @property
  def cache(self) -> Path: return self.root / 'cache'
  @property
  def imports(self) -> Path: return self.root / 'import'
  @property
  def backend(self) -> Path: return self.root / 'backend'
  @property
  def runtime(self) -> Path: return self.root / 'run'
  @property
  def status(self) -> Path: return self.root / 'run' / 'status.json'
  @property
  def log(self) -> Path: return self.root / 'run' / 'soloist.log'


def private_dir(path: Path) -> Path:
  path.mkdir(mode=0o700, parents=True, exist_ok=True)
  return path


def enabled(layout: Layout | None = None) -> bool:
  """Cheap manager predicate: one stat, no Params key, no JSON parsing."""
  return (layout or Layout.default()).enabled_flag.exists()
