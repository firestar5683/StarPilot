// Presentation only. No Params writes, telemetry collection or inferred mileage.
const FILTER_KEY = "galaxy.modelManager.hardwareFilter";
const FILTERS = new Set(["both", "gpu", "comma"]);

export function readHardwareFilter() {
  try {
    const value = localStorage.getItem(FILTER_KEY);
    return FILTERS.has(value) ? value : "both";
  } catch {
    return "both";
  }
}

export function saveHardwareFilter(value) {
  const filter = FILTERS.has(value) ? value : "both";
  try { localStorage.setItem(FILTER_KEY, filter); } catch { /* View still works without storage. */ }
  return filter;
}

export function matchesHardware(model, filter) {
  if (filter === "gpu") return model?.requiresGpu === true;
  if (filter === "comma") return model?.requiresGpu === false;
  return true;
}

export function hardwareLabel(model) {
  if (model?.requiresGpu === true) return "GPU · External";
  if (model?.requiresGpu === false) return "Comma · On-device";
  return "Hardware unknown";
}

function bytes(value) {
  return Number.isSafeInteger(value) && value > 0 ? value : null;
}

function formatBytes(value) {
  return value >= 1e9 ? `${(value / 1e9).toFixed(2)} GB` : `${(value / 1e6).toFixed(1)} MB`;
}

export function fileSizeText(model) {
  // modelSize is an architecture class, never a byte count.
  const installed = bytes(model?.fileSizeBytes);
  const declared = bytes(model?.declaredSizeBytes);
  const downloaded = bytes(model?.downloadedBytes);
  if (model?.partial || model?.sizeStatus === "partial") {
    return `Partial: ${downloaded ? formatBytes(downloaded) : "unknown"} / ${declared ? formatBytes(declared) : "unknown"}`;
  }
  if (installed && declared && installed !== declared) return `${formatBytes(installed)} · size mismatch`;
  if (installed) return formatBytes(installed);
  if (declared) return `${formatBytes(declared)} · declared`;
  return "Unavailable";
}
