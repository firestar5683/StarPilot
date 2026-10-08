"""Route metadata and recorded settings for disposable host replay."""

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence
import json
import math
import os
import stat
import sys

from openpilot.common.params import Params, ParamKeyType, UnknownKeyName
from openpilot.common.version import terms_version, training_version
from openpilot.starpilot.schema_cache import CACHE_KEYS, inspect_cache
from openpilot.tools.lib.logreader import LogReader, ReadMode, parse_direct, parse_indirect
from openpilot.tools.lib.route import SegmentRange


DEMO_ROUTE = "5beb9b58bd12b691/0000010a--a51155e496"
PRIVATE_KEYS = frozenset(("AccessToken", "GithubSshKeys", "GithubUsername", "SecOCKey", "PairingEmail",
                          "AthenadUploadQueue", "AthenadRecentlyViewedRoutes", "UsageStatsState", "UsageStatsStatus"))
MAX_PARAM_BYTES = 32 * 1024 * 1024
DEVICE_TYPES = frozenset(("tici", "tizi", "mici"))
VALUE_OPTIONS = frozenset(("-a", "--allow", "-b", "--block", "-c", "--cache", "-s", "--start",
                           "-x", "--playback", "-d", "--data_dir"))
FLAG_OPTIONS = frozenset(("--cabin", "--dcam", "--wide-road", "--ecam", "--no-loop", "--no-cache",
                          "--qcam", "--no-hw-decoder", "--no-vipc", "--all", "--benchmark"))


@dataclass(frozen=True)
class ReplayArgs:
  route: str | None
  data_dir: str | None
  auto_source: bool = False


def parse_replay_args(args: Sequence[str]) -> ReplayArgs:
  route = None
  data_dir = None
  auto_source = False
  index = 0
  while index < len(args):
    arg = args[index]
    if arg == "--demo":
      route = DEMO_ROUTE
    elif arg == "--auto":
      auto_source = True
    elif any(arg.startswith(f"{name}=") for name in ("--allow", "--block", "--cache", "--start", "--playback", "--data_dir")):
      name, _, value = arg.partition("=")
      if not value:
        raise ValueError(f"missing value for replay option {name}")
      if name == "--data_dir":
        data_dir = value
    elif arg in VALUE_OPTIONS:
      if index + 1 >= len(args):
        raise ValueError(f"missing value for replay option {arg}")
      if arg in ("-d", "--data_dir"):
        data_dir = args[index + 1]
      index += 1
    elif arg in FLAG_OPTIONS:
      pass
    elif arg.startswith("-"):
      raise ValueError(f"unsupported replay option {arg}")
    elif route is None:
      route = arg
    else:
      raise ValueError("replay accepts only one route")
    index += 1
  return ReplayArgs(route, data_dir, auto_source)


def first_log_identifier(replay: ReplayArgs) -> str | None:
  if replay.route is None or replay.auto_source:
    return None
  route = parse_indirect(replay.route)
  if parse_direct(route) is not None:
    return route
  try:
    segment_range = SegmentRange(route)
    fragment = segment_range.slice.split(":", 1)[0]
    segment = int(fragment) if fragment else 0
    if segment < 0:
      return None  # Avoid an unbounded remote segment lookup for metadata.
    if replay.data_dir:
      data_root = Path(replay.data_dir)
      route_token = segment_range.route_name.replace("/", "|")
      for suffix in ("rlog.zst", "rlog.bz2", "qlog.zst", "qlog.bz2"):
        for candidate in (data_root / f"{route_token}--{segment}" / suffix,
                          data_root / f"{segment_range.log_id}--{segment}" / suffix,
                          data_root / f"{route_token}--{segment}--{suffix}"):
          if candidate.is_file():
            return str(candidate)
      return None  # An explicitly local replay must not fetch metadata from a remote route.
    return f"{segment_range.route_name}/{segment}/{segment_range.selector or 'a'}"
  except (AssertionError, TypeError, ValueError):
    return None


def route_init_data(replay: ReplayArgs):
  identifier = first_log_identifier(replay)
  if identifier is None:
    return None
  try:
    return LogReader(identifier, default_mode=ReadMode.AUTO).first("initData")
  except Exception as error:
    print(f"Replay initData unavailable: {error}", file=sys.stderr)
    return None


def select_ui_target(init_data) -> str:
  return "c4" if str(getattr(init_data, "deviceType", "")).lower() in ("mici", "c4") else "c3"


def replay_device_type(init_data) -> str:
  value = str(getattr(init_data, "deviceType", "")).lower()
  return value if value in DEVICE_TYPES else "pc"


def seed_param(params: Params, key: str, raw: bytes) -> bool:
  if key in PRIVATE_KEYS or not raw or len(raw) > MAX_PARAM_BYTES:
    return False
  try:
    kind = params.get_type(key)
    if kind == ParamKeyType.BYTES:
      if key not in CACHE_KEYS or inspect_cache(key, raw).status != "valid":
        return False
      value = raw
    elif kind == ParamKeyType.BOOL:
      if raw not in (b"0", b"1"):
        return False
      value = raw == b"1"
    else:
      value = params.cpp2python(key, raw)
      if value is None or kind == ParamKeyType.FLOAT and not math.isfinite(value):
        return False
      if kind == ParamKeyType.JSON:
        json.dumps(value, allow_nan=False)
    params.put(key, value, block=True)
    return True
  except (UnknownKeyName, UnicodeError, TypeError, ValueError):
    return False


def seed_display_params(init_data, params: Params) -> int:
  """Restore registered typed settings and verified cache envelopes, never credentials."""
  try:
    entries = init_data.params.entries
  except (AttributeError, TypeError):
    return 0
  count = 0
  for entry in entries:
    name = str(entry.key)
    raw = bytes(entry.value)
    count += seed_param(params, name, raw)
  return count


def seed_snapshot(directory: str, params: Params) -> int:
  root = Path(directory)
  if not root.is_absolute() or not root.is_dir():
    raise ValueError("--params must name an absolute directory of saved Param files")
  count = 0
  for key in params.all_keys():
    name = key.decode()
    if name in PRIVATE_KEYS:
      continue
    try:
      fd = os.open(root / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
      continue
    try:
      info = os.fstat(fd)
      if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_PARAM_BYTES:
        raise ValueError(f"Invalid saved Param file: {name}")
      with os.fdopen(fd, "rb", closefd=False) as file:
        count += seed_param(params, name, file.read(MAX_PARAM_BYTES + 1))
    finally:
      os.close(fd)
  return count


def seed_preview(init_data, params: Params, snapshot: str | None = None) -> int:
  count = seed_display_params(init_data, params)
  if snapshot is not None:
    count += seed_snapshot(snapshot, params)
  for key, value in (("HasAcceptedTerms", terms_version), ("CompletedTrainingVersion", training_version)):
    if params.get(key) is None:
      params.put(key, value, block=True)
  return count
