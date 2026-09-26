from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class FavoriteAction:
  key: str
  label: str
  kind: str = "action"
  state_label: str = "Press"
  available: bool = False
  reason: str = "Unavailable in this context"
  token: str = ""
  invoke: Callable[[], bool] | None = field(default=None, compare=False, repr=False)
  section: str = "Actions"


@dataclass(frozen=True)
class FavoriteRequest:
  index: int
  key: str
  revision: str
  action_token: str


@dataclass(frozen=True)
class FavoriteSlot:
  index: int
  key: str | None = None
  label: str = ""
  enabled: bool = False
  show_onroad: bool = False
  kind: str = "action"
  state_label: str = "Not assigned"
  available: bool = False
  reason: str = "Choose a control"
  request: FavoriteRequest | None = None
  value: float | None = None


@dataclass(frozen=True)
class FavoriteSnapshot:
  slots: tuple[FavoriteSlot, ...]
  options: tuple[FavoriteAction, ...]
  revision: str
  configurable: bool
  valid: bool


@dataclass(frozen=True)
class FavoriteResult:
  success: bool
  message: str
  state_label: str = ""
