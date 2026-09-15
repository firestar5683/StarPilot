import math
import os
from starpilot.common.external_gpu_temperature import external_gpu_temperature
from starpilot.common.external_gpu_memory import external_gpu_memory
from collections.abc import Iterable
from typing import Any


def external_gpu_temperature_metric(sm, now_ns: int | None = None) -> str:
  """Read only published Chestnut hotspot telemetry; never open the GPU.

  SMU samples normally refresh every 10s; tolerate 5s scheduling margin.
  Check sample age separately from the 10Hz cached envelope. Old publishers
  without the sample timestamp deliberately display unavailable.
  """
  temperature, _ = external_gpu_temperature(sm, now_ns)
  return "eGPU: --" if temperature is None else f"eGPU: {round(temperature)}°C"


def external_gpu_memory_metric(sm, now_ns: int | None = None) -> str:
  memory, _ = external_gpu_memory(sm, now_ns)
  if memory is None:
    return "eGPU RAM: --"
  used, total = memory
  return f"eGPU RAM: {used / 2**30:.1f}/{total / 2**30:.1f} GiB ({round(100 * used / total)}%)"


def _finite_temperatures(values: Iterable[Any]) -> list[float]:
  temperatures = []
  for value in values:
    try:
      temperature = float(value)
    except (OverflowError, TypeError, ValueError):
      continue
    if math.isfinite(temperature) and temperature > 0.0:
      temperatures.append(temperature)
  return temperatures


def _usage_percent(value: Any) -> int:
  try:
    return max(0, min(100, int(value)))
  except (OverflowError, TypeError, ValueError):
    return 0


def _rounded_metric(value: Any) -> str:
  try:
    number = float(value)
  except (OverflowError, TypeError, ValueError):
    return "--"
  return str(round(number)) if math.isfinite(number) else "--"


def _usage_with_temperature(label: str, usage_percent: int, temperatures_c: Iterable[Any]) -> str:
  metric = f"{label}: {usage_percent}%"
  temperatures = _finite_temperatures(temperatures_c)
  if temperatures:
    metric += f" / {round(max(temperatures))}°C"
  return metric


def system_memory_total_gib() -> float:
  try:
    total_bytes = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
  except (OSError, TypeError, ValueError):
    return 0.0
  total_gib = float(total_bytes) / (1024.0 ** 3)
  return total_gib if math.isfinite(total_gib) and total_gib > 0.0 else 0.0


def build_developer_metric_parts(
  *,
  show_fps: bool,
  show_cpu: bool,
  show_gpu: bool,
  show_temp: bool,
  show_memory: bool,
  fps: float,
  min_fps: float,
  max_fps: float,
  avg_fps: float,
  cpu_usage_percent: Iterable[Any],
  cpu_temp_c: Iterable[Any],
  gpu_usage_percent: Any,
  gpu_temp_c: Iterable[Any],
  max_temp_c: Any,
  memory_usage_percent: Any,
  memory_total_gib: Any,
) -> list[str]:
  parts = []

  if show_cpu:
    cpu_values = [_usage_percent(value) for value in cpu_usage_percent]
    cpu_usage = int(sum(cpu_values) / len(cpu_values)) if cpu_values else 0
    parts.append(_usage_with_temperature("CPU", cpu_usage, cpu_temp_c))

  if show_gpu:
    parts.append(_usage_with_temperature("GPU", _usage_percent(gpu_usage_percent), gpu_temp_c))

  if show_temp:
    temperatures = _finite_temperatures([max_temp_c])
    parts.append(f"TEMP: {round(temperatures[0])}°C" if temperatures else "TEMP: --")

  if show_memory:
    memory_usage = _usage_percent(memory_usage_percent)
    try:
      total_gib = float(memory_total_gib)
    except (OverflowError, TypeError, ValueError):
      total_gib = 0.0
    if math.isfinite(total_gib) and total_gib > 0.0:
      memory_used_gib = total_gib * memory_usage / 100.0
      parts.append(f"RAM: {memory_used_gib:.1f}/{total_gib:.1f} GiB ({memory_usage}%)")
    else:
      parts.append(f"RAM: {memory_usage}%")

  if show_fps:
    parts += [
      f"FPS: {_rounded_metric(fps)}",
      f"Min: {_rounded_metric(min_fps)}",
      f"Max: {_rounded_metric(max_fps)}",
      f"Avg: {_rounded_metric(avg_fps)}",
    ]

  return parts
