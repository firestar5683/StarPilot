"""Route metadata and bounded saved-display seeding for disposable host replay."""

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence
import sys

from openpilot.common.params import Params
from openpilot.common.version import terms_version, training_version
from openpilot.tools.lib.logreader import LogReader, ReadMode, parse_direct, parse_indirect
from openpilot.tools.lib.route import SegmentRange


DEMO_ROUTE = "5beb9b58bd12b691/0000010a--a51155e496"
DISPLAY_BOOL_KEYS = frozenset(("IsMetric", "HideSpeed", "HideMaxSpeed", "HideSteeringWheel", "EnableTorqueBarWidget"))
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


def seed_display_params(init_data, params: Params) -> int:
  """Copy only exact, registered display booleans; no tokens or opaque docs."""
  try:
    entries = init_data.params.entries
  except (AttributeError, TypeError):
    return 0
  count = 0
  for entry in entries:
    name = str(entry.key)
    if name not in DISPLAY_BOOL_KEYS:
      continue
    raw = bytes(entry.value)
    if raw not in (b"0", b"1"):
      continue
    params.put_bool(name, raw == b"1", block=True)
    count += 1
  return count


def seed_preview(init_data, params: Params) -> int:
  count = seed_display_params(init_data, params)
  params.put("HasAcceptedTerms", terms_version, block=True)
  params.put("CompletedTrainingVersion", training_version, block=True)
  params.put_bool("OpenpilotEnabledToggle", True, block=True)
  return count
