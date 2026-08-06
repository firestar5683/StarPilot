import { html, reactive } from "/assets/vendor/arrow-core.js";

const CANVAS_W = 640;
const CANVAS_H = 480;
const ZOOM_MIN = 60;
const ZOOM_MAX = 640;
const ZOOM_STEP = 5;
let initialLoadTriggered = false;

const state = reactive({
  loading: false,
  error: "",
  success: "",
  armSide: null,
  leftCenter: null,
  rightCenter: null,
  zoom: 240,
  image: false,
  configSaved: false,
  configExists: false,
});

let _loadedImage = null;
let _lastCanvas = null;
let loadedConfig = null;

function getCanvas() {
  return document.getElementById("pip-sidecam-canvas");
}

function canvasScale() {
  const canvas = getCanvas();
  const img = _loadedImage;
  const nativeW = img ? img.naturalWidth : 1920;
  const nativeH = img ? img.naturalHeight : 1080;
  const cw = canvas ? canvas.width || CANVAS_W : CANVAS_W;
  const ch = canvas ? canvas.height || CANVAS_H : CANVAS_H;
  return { cw, ch, nativeW, nativeH };
}

function redraw() {
  const canvas = getCanvas();
  if (!canvas) return;

  if (canvas !== _lastCanvas) {
    _lastCanvas = canvas;
    if (_loadedImage) {
      canvas._img = _loadedImage;
      canvas.width = Math.min(_loadedImage.naturalWidth, 1280);
      canvas.height = Math.round(canvas.width * (_loadedImage.naturalHeight / _loadedImage.naturalWidth));
    } else {
      canvas.width = CANVAS_W;
      canvas.height = CANVAS_H;
    }
  }

  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const img = _loadedImage;
  if (img) {
    canvas._img = img;
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  } else {
    ctx.fillStyle = "#222";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#888";
    ctx.font = "16px monospace";
    ctx.textAlign = "center";
    ctx.fillText("Loading camera snapshot...", canvas.width / 2, canvas.height / 2);
    return;
  }

  const half = state.zoom / 2;
  const sides = [
    { key: "left", center: state.leftCenter, color: "#0d6efd", label: "LEFT WINDOW" },
    { key: "right", center: state.rightCenter, color: "#fd7e14", label: "RIGHT WINDOW" },
  ];

  for (const side of sides) {
    if (!side.center) continue;

    const [cx, cy] = side.center;

    // Crop square (what gets sampled) + circular bubble overlay.
    ctx.strokeStyle = side.color;
    ctx.lineWidth = 2;
    ctx.setLineDash([]);
    ctx.strokeRect(cx - half, cy - half, state.zoom, state.zoom);

    ctx.beginPath();
    ctx.arc(cx, cy, half, 0, Math.PI * 2);
    ctx.fillStyle = side.color + "40";
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = side.color;
    ctx.stroke();

    // Center dot
    ctx.beginPath();
    ctx.arc(cx, cy, 4, 0, Math.PI * 2);
    ctx.fillStyle = "#fff";
    ctx.fill();
    ctx.strokeStyle = side.color;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Label
    ctx.fillStyle = side.color;
    ctx.font = "bold 13px monospace";
    ctx.textAlign = "center";
    ctx.fillText(side.label, cx, cy - half - 8);
  }

  if (state.armSide) {
    ctx.fillStyle = "#fff";
    ctx.font = "bold 15px monospace";
    ctx.textAlign = "center";
    ctx.fillText(
      state.armSide === "left" ? "Click to set LEFT window center" : "Click to set RIGHT window center",
      canvas.width / 2,
      canvas.height - 18,
    );
  }
}

async function loadSnapshot() {
  state.error = "";
  state.success = "";
  state.image = false;
  let blobUrl = null;
  try {
    const resp = await fetch("/api/pip_preview/snapshot");
    if (!resp.ok) {
      const payload = await resp.json().catch(() => ({}));
      throw new Error(payload.error || resp.statusText || "Failed to load snapshot");
    }

    let src;
    const contentType = resp.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const data = await resp.json();
      if (!data.jpeg) throw new Error("Snapshot missing image data");
      src = `data:image/jpeg;base64,${data.jpeg}`;
    } else {
      const blob = await resp.blob();
      blobUrl = URL.createObjectURL(blob);
      src = blobUrl;
    }

    const img = new Image();
    img.onload = () => {
      _loadedImage = img;
      const canvas = getCanvas();
      if (canvas) {
        canvas._img = img;
        canvas.width = Math.min(img.naturalWidth, 1280);
        canvas.height = Math.round(canvas.width * (img.naturalHeight / img.naturalWidth));
      }
      state.image = true;
      state.success = "Camera snapshot loaded. Place a center point on each window, then adjust the zoom.";
      applyConfigToCanvas();
      requestAnimationFrame(redraw);
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
        blobUrl = null;
      }
    };
    img.onerror = () => {
      state.image = false;
      state.error = "Failed to decode image";
      requestAnimationFrame(redraw);
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
        blobUrl = null;
      }
    };
    img.src = src;
  } catch (e) {
    state.image = false;
    state.error = e.message;
    requestAnimationFrame(redraw);
    if (blobUrl) {
      URL.revokeObjectURL(blobUrl);
      blobUrl = null;
    }
  }
}

function canvasClick(e) {
  if (!state.image || !state.armSide || !e) return;
  const canvas = getCanvas();
  if (!canvas) return;

  const rect = canvas.getBoundingClientRect();
  const x = Math.round((e.clientX - rect.left) * (canvas.width / rect.width));
  const y = Math.round((e.clientY - rect.top) * (canvas.height / rect.height));
  if (x < 0 || y < 0) return;

  if (state.armSide === "left") {
    state.leftCenter = [x, y];
  } else {
    state.rightCenter = [x, y];
  }
  state.armSide = null;
  state.error = "";
  requestAnimationFrame(redraw);
}

function setArm(e) {
  const side = e?.currentTarget?.value || e?.target?.value;
  if (!side) return;
  state.armSide = side;
  state.error = "";
  state.success = "";
  requestAnimationFrame(redraw);
}

function updateZoom(e) {
  const value = Number(e?.currentTarget?.value ?? e?.target?.value ?? 0);
  if (!Number.isFinite(value)) return;
  state.zoom = value;
  requestAnimationFrame(redraw);
}

function clearCenter(side) {
  if (side === "left") {
    state.leftCenter = null;
  } else {
    state.rightCenter = null;
  }
  if (state.armSide === side) state.armSide = null;
  requestAnimationFrame(redraw);
}

function clearAll() {
  state.leftCenter = null;
  state.rightCenter = null;
  state.armSide = null;
  state.configSaved = false;
  requestAnimationFrame(redraw);
}

async function saveConfig() {
  if (!state.leftCenter && !state.rightCenter) {
    state.error = "Place at least one center point.";
    return;
  }

  const { cw, ch, nativeW, nativeH } = canvasScale();

  function toNative(center) {
    if (!center) return [];
    return [Math.round(center[0] * nativeW / cw), Math.round(center[1] * nativeH / ch)];
  }

  const config = {
    width: nativeW,
    height: nativeH,
    center_left: toNative(state.leftCenter),
    center_right: toNative(state.rightCenter),
    crop_size: Math.round(state.zoom * nativeW / cw),
  };

  state.loading = true;
  state.error = "";
  state.success = "";
  try {
    const resp = await fetch("/api/pip_preview/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "Failed to save");
    state.configSaved = true;
    state.configExists = true;
    state.success = "PiP Preview mask saved!";
    await loadExistingConfig();
  } catch (e) {
    state.error = e.message;
  }
  state.loading = false;
}

async function loadExistingConfig() {
  try {
    const resp = await fetch("/api/pip_preview/config");
    if (!resp.ok) return;
    const config = await resp.json();
    loadedConfig = config;
    applyConfigToCanvas();
  } catch (e) {
    console.error("PiP Preview config load failed", e);
  }
}

function applyConfigToCanvas() {
  const config = loadedConfig;
  if (!config) {
    state.leftCenter = null;
    state.rightCenter = null;
    state.configExists = false;
    redraw();
    return;
  }

  const { cw, ch, nativeW, nativeH } = canvasScale();

  function toCanvas(center) {
    if (!Array.isArray(center) || center.length < 2) return null;
    return [Math.round(center[0] * cw / nativeW), Math.round(center[1] * ch / nativeH)];
  }

  state.leftCenter = toCanvas(config.center_left);
  state.rightCenter = toCanvas(config.center_right);
  if (Number.isFinite(Number(config.crop_size))) {
    state.zoom = Math.round(Number(config.crop_size) * cw / nativeW);
  }
  state.configExists = Boolean(state.leftCenter || state.rightCenter);
  redraw();
}

async function deleteConfig() {
  state.loading = true;
  state.error = "";
  state.success = "";
  try {
    const resp = await fetch("/api/pip_preview/config", { method: "DELETE" });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "Failed to delete");
    state.leftCenter = null;
    state.rightCenter = null;
    state.armSide = null;
    state.configSaved = false;
    state.configExists = false;
    loadedConfig = null;
    state.success = "PiP Preview mask cleared.";
    requestAnimationFrame(redraw);
  } catch (e) {
    state.error = e.message;
  }
  state.loading = false;
}

function scheduleInitialLoad() {
  if (!initialLoadTriggered) {
    initialLoadTriggered = true;
    loadExistingConfig();
    loadSnapshot();
  }
  const attempt = () => {
    if (getCanvas()) {
      redraw();
      return;
    }
    requestAnimationFrame(attempt);
  };
  requestAnimationFrame(attempt);
}

function retrySnapshot() {
  state.error = "";
  state.success = "";
  loadSnapshot();
}

export function PipSideCamera() {
  const el = html`
    <div class="v-asm-wrapper">
      <div class="v-asm-section">
        <div class="v-asm-header">
          <h2>PiP Side Camera Preview</h2>

          <div class="v-asm-card v-asm-card-info">
            <div class="v-asm-card-title">About PiP Preview</div>
            <ul class="v-asm-card-list">
              <li>Shows a temporary Picture-in-Picture bubble of the adjacent side window while the turn signal is on or a blind spot is detected</li>
              <li>Place a single center point on each window, then pick a shared zoom level</li>
              <li>This mask is separate from the V-ASM detection mask, so you can tune the visual crop independently</li>
              <li>Works alongside factory blind spot monitoring and/or V-ASM, and with turn signals alone</li>
            </ul>
          </div>

          <div class="v-asm-card v-asm-card-danger">
            <div class="v-asm-card-title">Setup</div>
            <ul class="v-asm-card-list">
              <li>Click "Set Left Center", then click the driver's side window; repeat for the right window</li>
              <li>From the driver camera, the car's LEFT window appears on the right side of the image and vice versa</li>
              <li>The zoom slider applies to BOTH windows so the preview stays consistent</li>
              <li>At least one window center is required to enable the preview</li>
            </ul>
          </div>

        </div>

        <div class="v-asm-note">
          Use the preview to enhance lateral awareness. Always check manually before merging and be aware the driver camera view is from the cabin and does not reflect your blind spot.
        </div>

        ${state.error ? html`<div class="v-asm-error-banner">${state.error}</div>` : ""}
        ${state.success ? html`<div class="v-asm-success-banner">${state.success}</div>` : ""}
        ${state.configSaved ? html`
          <div class="v-asm-success-banner">
            PiP Preview mask saved! Configure the preview in <a href="/device_settings/visual-display-ui">Toggles</a>.
          </div>
        ` : ""}

        <div class="v-asm-toolbar">
          <div class="v-asm-btn-group">
            <button class="${state.armSide === "left" ? "v-asm-btn v-asm-btn-left-active" : "v-asm-btn v-asm-btn-outline-left"}"
                    @click="${setArm}" value="left">
              ${state.leftCenter ? "Move Left Center" : "Set Left Center"}
            </button>
            <button class="${state.armSide === "right" ? "v-asm-btn v-asm-btn-right-active" : "v-asm-btn v-asm-btn-outline-right"}"
                    @click="${setArm}" value="right">
              ${state.rightCenter ? "Move Right Center" : "Set Right Center"}
            </button>

            <button class="v-asm-btn v-asm-btn-primary" @click="${saveConfig}" .disabled="${state.loading || (!state.leftCenter && !state.rightCenter)}">
              ${state.loading ? "Saving..." : "Save Mask"}
            </button>
            ${state.configExists ? html`<button class="v-asm-btn v-asm-btn-danger" @click="${deleteConfig}" .disabled="${state.loading}">Delete Mask</button>` : ""}
            <button class="v-asm-btn v-asm-btn-secondary" @click="${clearAll}">Clear All</button>
            <button class="v-asm-btn v-asm-btn-secondary" @click="${retrySnapshot}" .disabled="${state.loading}">
              ${state.loading ? "Loading..." : "Get a new Snapshot"}
            </button>
          </div>
        </div>

        ${state.armSide ? html`<div class="v-asm-mode-banner ${state.armSide === "left" ? "v-asm-mode-left" : "v-asm-mode-right"}"><span>${state.armSide === "left" ? "⬅ Placing Left Center" : "➡ Placing Right Center"}</span><span>Click on the window to place its center point</span></div>` : ""}

        <div class="v-asm-canvas-wrapper">
          <canvas id="pip-sidecam-canvas" @click="${canvasClick}"></canvas>
          <div class="v-asm-instructions">
            ${state.armSide ? "Click the window to place its center point." : "Place a center point on each window, then use the zoom slider below."}
          </div>
        </div>

        <div class="pip-zoom-control">
          <div class="pip-zoom-header">
            <span>Zoom</span>
            <span class="pip-zoom-value">${() => state.zoom} px</span>
          </div>
          <input type="range" class="pip-zoom-slider" min="${ZOOM_MIN}" max="${ZOOM_MAX}" step="${ZOOM_STEP}"
                 value="${() => state.zoom}" @input="${updateZoom}" />
          <div class="pip-zoom-labels">
            <span>Wide</span>
            <span>Close</span>
          </div>
          <div class="pip-zoom-hint">Applied to both windows so the preview stays consistent.</div>
        </div>
      </div>

      <div class="v-asm-card v-asm-card-warning">
        <div class="v-asm-card-title">Preview Settings</div>
        <ul class="v-asm-card-list">
          <li>Enable "PiP Side Preview" in <a href="/device_settings/visual-display-ui">Toggles -> Visual (Display & UI) -> Driving Screen Widgets</a></li>
          <li>Choose to show the preview on the turn signal, on blind spot detection, or both</li>
        </ul>
      </div>
    </div>
  `;

  scheduleInitialLoad();
  return el;
}
