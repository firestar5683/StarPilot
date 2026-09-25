"""One read-only model snapshot adapter for native UI and authenticated Galaxy."""

from collections.abc import Callable
from pathlib import Path
import time
from typing import Any

from openpilot.cereal.services import SERVICE_LIST
from openpilot.starpilot.models.catalog import CATALOG
from openpilot.starpilot.models.receipt import process_start_ticks, read_receipt
from openpilot.starpilot.models.status import ModelLoad, ModelOutput, ModelProcess, ModelStatus, project_status


MODEL_SERVICES = ("managerState", "modelV2", "drivingModelData")


def _stamp(sm: Any, service: str, now_mono_ns: int) -> tuple[int, bool]:
  try:
    stamp = sm.logMonoTime[service]
    valid = (type(stamp) is int and 0 < stamp <= now_mono_ns and bool(sm.valid[service]) and
             bool(sm.alive[service]) and now_mono_ns - stamp <= int(2e9 / SERVICE_LIST[service].frequency))
    return stamp if type(stamp) is int else 0, valid
  except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
    return 0, False


def _process(sm: Any, now_mono_ns: int, start_ticks: Callable[[int], int]) -> ModelProcess | None:
  if not _stamp(sm, "managerState", now_mono_ns)[1]:
    return None
  try:
    processes = [state for state in sm["managerState"].processes if state.name == "modeld"]
    if len(processes) != 1:
      return None
    state = processes[0]
    pid = int(state.pid)
    if not state.running or pid <= 0:
      return None
    return ModelProcess(pid, start_ticks(pid), True)
  except (AttributeError, KeyError, TypeError, ValueError, OSError):
    return None


def _output(sm: Any, params: Any, now_mono_ns: int) -> ModelOutput | None:
  model_stamp, model_valid = _stamp(sm, "modelV2", now_mono_ns)
  driving_stamp, driving_valid = _stamp(sm, "drivingModelData", now_mono_ns)
  if model_stamp == 0 and driving_stamp == 0:
    return None
  try:
    raw_chestnut = params.get("ChestnutActive")
    chestnut = (raw_chestnut if type(raw_chestnut) is bool else
                None if raw_chestnut not in (None, b"0", b"1") else raw_chestnut == b"1")
    big = bool(sm["modelV2"].big) if model_stamp else False
    return ModelOutput(model_stamp, model_valid, driving_stamp, driving_valid, big, chestnut)
  except (AttributeError, KeyError, TypeError, ValueError, OSError):
    return None


def snapshot(sm: Any, params: Any, now_mono_ns: int, *, requested_id: str | None = None,
             receipt_file: Path | None = None, start_ticks: Callable[[int], int] = process_start_ticks,
             read_load: Callable[[Path | None], ModelLoad | None] = read_receipt) -> ModelStatus:
  """Sample one manager process and two live model outputs; never infer a load from Params."""
  process = _process(sm, now_mono_ns, start_ticks)
  output = _output(sm, params, now_mono_ns) if process is not None else None
  load = read_load(receipt_file) if process is not None else None
  return project_status(requested_id, process, load, output, now_mono_ns)


class ModelStatusSource:
  """Independent optional subscriber; it does not affect UI/global service health."""

  def __init__(self, params: Any, sm: Any | None = None, clock: Callable[[], int] = time.monotonic_ns):
    if sm is None:
      from openpilot.cereal import messaging
      sm = messaging.SubMaster(list(MODEL_SERVICES))
    self.sm = sm
    self.params = params
    self.clock = clock

  def snapshot(self) -> ModelStatus:
    self.sm.update(0)
    from openpilot.selfdrive.modeld.helpers import chestnut_present
    from openpilot.starpilot.models.manager import requested_runtime_id
    return snapshot(self.sm, self.params, self.clock(), requested_id=requested_runtime_id(chestnut_present()))

  def json(self) -> dict[str, object]:
    status = self.snapshot()
    return {"schemaVersion": 1, "catalog": [{"id": entry.model_id, "name": entry.name,
                                              "selectable": entry.selectable} for entry in CATALOG],
            "requestedId": status.requested_id, "loadedId": status.loaded_id,
            "variant": status.variant.value if status.variant is not None else None,
            "health": status.health.value, "fallbackReason": status.fallback_reason,
            "artifactSha256": status.artifact_sha256, "pendingNextStart": status.pending_next_start}

  def close(self) -> None:
    self.sm = None
