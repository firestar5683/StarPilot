"""Driving health requirements for manager-owned services."""

# Projection is optional even when the user has requested the service to run.
# Its lifecycle remains visible in managerState and Android Auto's own status.
ANCILLARY_PROCESSES = frozenset({'android_autod'})


def driving_process_failures(processes) -> set[str]:
  return {process.name for process in processes
          if process.shouldBeRunning and not process.running and process.name not in ANCILLARY_PROCESSES}
