"""Finish a settings restore through the existing model downloader."""
import threading
import time


def _downloadable(entries):
  # An unfetched catalog still lists Galaxy's built-in model.
  return any(not model.get("builtin") or model.get("modelLabArtifactAvailable") for model in entries)


def _supervised(task, *, check_parked, abort, monotonic, timeout, poll=0.5, join_timeout=60):
  """Run a blocking task under the parked and timeout guards; returns its exception, if any."""
  outcome = []

  def run():
    try:
      task()
    except Exception as exc:
      outcome.append(exc)

  worker = threading.Thread(target=run, name="restore-model-refresh", daemon=True)
  worker.start()
  deadline = monotonic() + timeout
  try:
    while worker.is_alive():
      check_parked()
      if monotonic() >= deadline:
        raise ValueError("Timed out refreshing the model list. Check Model Manager before retrying.")
      worker.join(poll)
  except BaseException:
    abort()
    # Bound the wait: a wedged refresh must not hold the restore workflow forever.
    worker.join(join_timeout)
    if worker.is_alive():
      raise ValueError("Refreshing the model list did not stop. Reboot before retrying.") from None
    raise
  return outcome[0] if outcome else None


def download_saved_models(models, *, catalog, queue, cancel, owns, busy, progress, check_parked, reboot, report,
                          refresh=None, abort_refresh=lambda: None, canonical=str, cancelled=lambda: False,
                          sleep=time.sleep, monotonic=time.monotonic, timeout=1800):
  """Download saved models by catalog ID, then reboot. Unoffered models are skipped and reported.

  Archives never supply URLs, and saved versions are informational since the downloader serves the
  catalog's version. Reboot only after every attempted download is verified.
  """
  check_parked()
  if busy():
    raise ValueError("Another model download is active. Wait for it to finish and retry.")
  entries = catalog()
  # Refresh only an unfetched catalog: a refresh can migrate artifacts and download the selected model itself.
  if models and refresh is not None and not _downloadable(entries):
    report("Refreshing the model list...")
    error = _supervised(refresh, check_parked=check_parked, abort=abort_refresh, monotonic=monotonic, timeout=timeout)
    if error is not None:
      report(f"Could not refresh model list: {error}. Checking the cached catalog...")
    check_parked()
    entries = catalog()
  if models and not _downloadable(entries):
    raise ValueError("The downloadable model catalog is unavailable. Connect to the internet and retry, or reboot without downloading.")
  current = {model["value"]: model for model in entries}

  pending = []
  skipped = []
  for saved in models:
    key = canonical(saved["key"])
    model = current.get(key)
    if model is None:
      skipped.append(f"{key} (no longer offered)")
      continue
    for variant, installed in (("standard", "installed"), ("lab", "modelLabArtifactInstalled")):
      if not saved[variant] or model.get(installed):
        continue
      if variant == "standard" and model.get("requiresGpu") and not model.get("gpuAvailable"):
        skipped.append(f"{key} (needs a detected external GPU)")
      elif variant == "lab" and (not model.get("modelLabArtifactAvailable") or not model.get("modelLabEligible", True)):
        skipped.append(f"{key} eGPU variant (unavailable)")
      else:
        pending.append((key, variant, installed))

  failed = []
  for index, (key, variant, installed) in enumerate(pending):
    check_parked()
    if busy():
      raise ValueError("Another model download is active. Wait for it to finish and retry.")
    label = f"{key}{' (eGPU)' if variant == 'lab' else ''}"
    report(f"Downloading {index + 1}/{len(pending)}: {label}")
    try:
      token = queue(key, variant)
    except ValueError as exc:
      if busy():
        raise ValueError("Another model download started. Wait for it to finish and retry.") from exc
      failed.append(f"'{label}' ({exc})")
      continue
    deadline = monotonic() + timeout
    try:
      while owns(token):
        check_parked()
        if monotonic() >= deadline:
          raise ValueError(f"Timed out downloading '{label}'. Check Model Manager before retrying.")
        sleep(1)
    except BaseException:
      cancel(token)  # Cancels only our request, never a newer one.
      raise
    if cancelled():
      raise ValueError("Restore model downloads were cancelled. Retry or reboot without downloading.")
    model = next((entry for entry in catalog() if entry["value"] == key), {})
    if not model.get(installed):
      failed.append(f"'{label}' ({progress() or 'download did not complete'})")

  check_parked()
  skipped_note = f"Skipped {len(skipped)} unavailable model(s): {', '.join(skipped)}." if skipped else ""
  if failed:
    raise ValueError(" ".join(filter(None, [f"Could not download {', '.join(failed)}.", skipped_note,
                                            "Retry, or reboot without downloading."])))
  if busy():
    raise ValueError("Another download started. Wait for it to finish before rebooting.")
  reboot(f"{skipped_note} Install them from Model Manager after reboot." if skipped else "")
