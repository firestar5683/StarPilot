"""Driving health requirements for manager-owned services."""

# Projection and local phone access are optional even when requested.
# Their lifecycles remain visible in managerState and their own status.
ANCILLARY_PROCESSES = frozenset({'android_autod', 'galaxy_hotspot'})


def driving_process_failures(processes) -> set[str]:
  return {process.name for process in processes
          if process.shouldBeRunning and not process.running and process.name not in ANCILLARY_PROCESSES}
