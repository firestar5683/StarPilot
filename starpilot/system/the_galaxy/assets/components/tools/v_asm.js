import { html, reactive } from "/assets/vendor/arrow-core.js";

const CANVAS_W = 640;
const CANVAS_H = 480;
let pollInterval = null;
let pollHasBeenActive = false;
let initialLoadTriggered = false;

const state = reactive({
  loading: false,
  error: "",
  success: "",
  annotating: null,
  leftPoints: [],
  rightPoints: [],
  image: false,
  configSaved: false,
  configExists: false,
});

let _loadedImage = null;
let _lastCanvas = null;
let loadedConfig = null;

function polyCenter(pts) {
  if (!pts || pts.length === 0) return null;
  const cx = pts.reduce((s, p) => s + p[0], 0) / pts.length;
  const cy = pts.reduce((s, p) => s + p[1], 0) / pts.length;
  return [cx, cy];
}

function getCanvas() {
  return document.getElementById("v-asm-canvas");
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

  const sides = [
    { key: "left", points: state.leftPoints, fillColor: "rgba(13, 110, 253, 0.25)", borderColor: "#0d6efd", label: "LEFT" },
    { key: "right", points: state.rightPoints, fillColor: "rgba(253, 126, 20, 0.25)", borderColor: "#fd7e14", label: "RIGHT" },
  ];

  for (const side of sides) {
    if (side.points.length < 2) {
      for (const pt of side.points) {
        ctx.beginPath();
        ctx.arc(pt[0], pt[1], 5, 0, Math.PI * 2);
        ctx.fillStyle = side.borderColor;
        ctx.fill();
      }
      continue;
    }

    ctx.beginPath();
    ctx.moveTo(side.points[0][0], side.points[0][1]);
    for (let i = 1; i < side.points.length; i++) {
      ctx.lineTo(side.points[i][0], side.points[i][1]);
    }
    if (side.points.length >= 3) {
      ctx.closePath();
      ctx.fillStyle = side.fillColor;
      ctx.fill();
    }
    ctx.strokeStyle = side.borderColor;
    ctx.lineWidth = 2;
    ctx.stroke();

    for (const pt of side.points) {
      ctx.beginPath();
      ctx.arc(pt[0], pt[1], 4, 0, Math.PI * 2);
      ctx.fillStyle = "#fff";
      ctx.fill();
      ctx.strokeStyle = side.borderColor;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    if (side.points.length >= 3) {
      const center = polyCenter(side.points);
      if (center) {
        ctx.fillStyle = "#fff";
        ctx.font = "bold 14px monospace";
        ctx.textAlign = "center";
        ctx.fillText(side.label, center[0], center[1] + 5);
      }
    }
  }
}

async function loadSnapshot() {
  state.error = "";
  state.success = "";
  state.image = false;
  let blobUrl = null;
  try {
    const resp = await fetch("/api/v_asm/snapshot");
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
      state.success = "Camera snapshot loaded. Click a window button above to start annotating.";
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
  if (!state.annotating || !e || !state.image) return;
  const canvas = getCanvas();
  if (!canvas) return;

  const rect = canvas.getBoundingClientRect();
  const x = Math.round((e.clientX - rect.left) * (canvas.width / rect.width));
  const y = Math.round((e.clientY - rect.top) * (canvas.height / rect.height));

  if (x < 0 || y < 0) return;

  const points = state.annotating === "left" ? [...state.leftPoints] : [...state.rightPoints];

  if (points.length >= 3) {
    const first = points[0];
    const dist = Math.sqrt((x - first[0]) ** 2 + (y - first[1]) ** 2);
    if (dist < 12) {
      finishSide();
      return;
    }
  }

  points.push([x, y]);

  if (state.annotating === "left") {
    state.leftPoints = points;
  } else {
    state.rightPoints = points;
  }
  requestAnimationFrame(redraw);
}

function canvasRightClick(e) {
  if (!state.annotating || !e) return;
  e.preventDefault();
  const pts = state.annotating === "left" ? [...state.leftPoints] : [...state.rightPoints];
  if (!pts.length) return;
  pts.pop();
  if (state.annotating === "left") {
    state.leftPoints = pts;
  } else {
    state.rightPoints = pts;
  }
  requestAnimationFrame(redraw);
}

function startAnnotate(e) {
  const side = e?.currentTarget?.value || e?.target?.value;
  if (!side) return;
  state.annotating = side;
  state.error = "";
  state.success = "";
  requestAnimationFrame(redraw);
}

function finishSide() {
  if (!state.annotating) return;
  const side = state.annotating;
  const points = side === "left" ? state.leftPoints : state.rightPoints;
  if (points.length < 3) {
    state.error = "Need at least 3 points to define a region.";
    return;
  }
  state.annotating = null;
  state.success = `${side === "left" ? "Left" : "Right"} window annotated (${points.length} points)!`;
  requestAnimationFrame(redraw);
}

function clearSide(side) {
  if (side === "left") {
    state.leftPoints = [];
  } else {
    state.rightPoints = [];
  }
  state.annotating = null;
  requestAnimationFrame(redraw);
}

function clearAll() {
  state.leftPoints = [];
  state.rightPoints = [];
  state.annotating = null;
  state.configSaved = false;
  requestAnimationFrame(redraw);
}

async function saveConfig() {
  if (state.leftPoints.length < 3 && state.rightPoints.length < 3) {
    state.error = "Annotate at least one window with 3+ points.";
    return;
  }

  const canvas = getCanvas();
  const img = _loadedImage;
  const nativeW = img ? img.naturalWidth : 1920;
  const nativeH = img ? img.naturalHeight : 1080;
  const cw = canvas ? canvas.width : nativeW;
  const ch = canvas ? canvas.height : nativeH;

  function scalePoints(pts) {
    return pts.map(([x, y]) => [Math.round(x * nativeW / cw), Math.round(y * nativeH / ch)]);
  }

  const config = {
    width: nativeW,
    height: nativeH,
  };
  if (state.leftPoints.length >= 3) {
    config.poly_left = scalePoints(state.leftPoints);
  } else {
    config.poly_left = [];
  }
  if (state.rightPoints.length >= 3) {
    config.poly_right = scalePoints(state.rightPoints);
  } else {
    config.poly_right = [];
  }

  state.loading = true;
  state.error = "";
  state.success = "";
  try {
    const resp = await fetch("/api/v_asm/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "Failed to save");
    state.configSaved = true;
    state.configExists = true;
    state.success = "Annotation config saved! V-ASM is now enabled.";
    await loadExistingConfig();
  } catch (e) {
    state.error = e.message;
  }
  state.loading = false;
}

async function loadExistingConfig() {
  try {
    const resp = await fetch("/api/v_asm/config");
    if (!resp.ok) return;
    const config = await resp.json();
    loadedConfig = config;
    applyConfigToCanvas();
  } catch (e) {
    console.error("V-ASM config load failed", e);
  }
}

function applyConfigToCanvas() {
  const config = loadedConfig;
  if (!config) {
    state.leftPoints = [];
    state.rightPoints = [];
    state.configExists = false;
    redraw();
    return;
  }

  const canvas = getCanvas();
  const cw = canvas ? canvas.width || CANVAS_W : CANVAS_W;
  const ch = canvas ? canvas.height || CANVAS_H : CANVAS_H;
  const nativeW = _loadedImage ? _loadedImage.naturalWidth : (config.width || 1920);
  const nativeH = _loadedImage ? _loadedImage.naturalHeight : (config.height || 1080);
  const scaleX = cw / nativeW;
  const scaleY = ch / nativeH;

  const left = Array.isArray(config.poly_left) && config.poly_left.length >= 3
    ? config.poly_left.map(([x, y]) => [Math.round(x * scaleX), Math.round(y * scaleY)])
    : [];
  const right = Array.isArray(config.poly_right) && config.poly_right.length >= 3
    ? config.poly_right.map(([x, y]) => [Math.round(x * scaleX), Math.round(y * scaleY)])
    : [];

  state.leftPoints = left;
  state.rightPoints = right;
  state.configExists = Boolean(left.length || right.length);
  redraw();
}

async function deleteConfig() {
  state.loading = true;
  state.error = "";
  state.success = "";
  try {
    const resp = await fetch("/api/v_asm/config", { method: "DELETE" });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "Failed to delete");
    state.leftPoints = [];
    state.rightPoints = [];
    state.annotating = null;
    state.configSaved = false;
    state.configExists = false;
    loadedConfig = null;
    state.success = "Annotation config cleared.";
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

export function VASMAnnotations() {
  const el = html`
    <div class="v-asm-wrapper">
      <div class="v-asm-section">
        <div class="v-asm-header">
          <h2>Vision Adjacent Spot Monitoring (V-ASM)</h2>

          <div class="v-asm-card v-asm-card-info">
            <div class="v-asm-card-title">About V-ASM</div>
            <ul class="v-asm-card-list">
              <li>Camera-based adjacent spot monitoring using the driver camera, works alongside factory blind spot monitoring or standalone</li>
              <li>Annotate window areas so V-ASM knows where to look</li>
              <li>Massive thanks to those who contributed to our total of 65GB of training data (over 36GB from your submissions). If performance is lacking, submit edge case routes via the repo form or give feedback in the StarPilot Discord.</li>
              <li class="v-asm-card-action">Submit edge cases, learn about training pipeline, and data handling within the form at <a href="https://github.com/prabhaavp/vasm-op" target="_blank" rel="noopener noreferrer">github.com/prabhaavp/vasm-op</a></li>
            </ul>
          </div>

          <div class="v-asm-card v-asm-card-danger">
            <div class="v-asm-card-title">Tracing Guidelines</div>
            <ul class="v-asm-card-list">
              <li>Trace the visible glass (front and rear side windows on each side, as seen by the driver camera). Mask as much of the window area as possible.</li>
              <li>Exclude A-pillars, door frames, and interior. Include the side mirror if visible through the glass.</li>
              <li>The B-pillar is fine to include if needed for a continuous mask. Your head or body being in frame is fine (that is part of the training data). Be consistent left vs right.</li>
            </ul>
          </div>

        </div>

        <div class="v-asm-note">
          V-ASM is like a friend saying, "Hol' up, I don't think you're clear." Always check before merging and be aware false positives/negatives are possible.
        </div>

        ${state.error ? html`<div class="v-asm-error-banner">${state.error}</div>` : ""}
        ${state.success ? html`<div class="v-asm-success-banner">${state.success}</div>` : ""}
        ${state.configSaved ? html`
          <div class="v-asm-success-banner">
            Annotations saved! V-ASM is now enabled. Configure sensitivity in <a href="/device_settings/lateral-steering">Toggles -> Lateral</a>.
          </div>
        ` : ""}

        <div class="v-asm-toolbar">
          <div class="v-asm-btn-group">
            <button class="${state.annotating === "left" ? "v-asm-btn v-asm-btn-left-active" : "v-asm-btn v-asm-btn-outline-left"}"
                    @click="${startAnnotate}" value="left">
              ${state.annotating === "left" ? "Annotating Left..." : "Annotate Left"}
            </button>
            <button class="${state.annotating === "right" ? "v-asm-btn v-asm-btn-right-active" : "v-asm-btn v-asm-btn-outline-right"}"
                    @click="${startAnnotate}" value="right">
              ${state.annotating === "right" ? "Annotating Right..." : "Annotate Right"}
            </button>
            ${state.annotating ? html`<button class="v-asm-btn v-asm-btn-primary" @click="${finishSide}">Finish ${state.annotating === "left" ? "Left" : "Right"}</button>` : ""}

            <button class="v-asm-btn v-asm-btn-primary" @click="${saveConfig}" .disabled="${state.loading || (state.leftPoints.length < 3 && state.rightPoints.length < 3)}">
              ${state.loading ? "Saving..." : "Save Config"}
            </button>
            ${state.configExists ? html`<button class="v-asm-btn v-asm-btn-danger" @click="${deleteConfig}" .disabled="${state.loading}">Delete Config</button>` : ""}
            <button class="v-asm-btn v-asm-btn-secondary" @click="${clearAll}">Clear All</button>
          </div>

          <div class="v-asm-points-summary">
            <div class="v-asm-summary-badge badge-left">
              <span>Left: ${state.leftPoints.length} pt${state.leftPoints.length !== 1 ? "s" : ""}</span>
              ${state.leftPoints.length >= 3 ? html`<span class="badge-done">✔</span>` : ""}
              ${state.leftPoints.length > 0 ? html`<button class="v-asm-mini-clear" @click="${() => clearSide("left")}">×</button>` : ""}
            </div>
            <div class="v-asm-summary-badge badge-right">
              <span>Right: ${state.rightPoints.length} pt${state.rightPoints.length !== 1 ? "s" : ""}</span>
              ${state.rightPoints.length >= 3 ? html`<span class="badge-done">✔</span>` : ""}
              ${state.rightPoints.length > 0 ? html`<button class="v-asm-mini-clear" @click="${() => clearSide("right")}">×</button>` : ""}
            </div>
          </div>
        </div>

        ${state.annotating === "left" ? html`<div class="v-asm-mode-banner v-asm-mode-left"><span>⬅ Annotating Left Window</span><span>Click the canvas to place points around the visible glass</span></div>`
          : state.annotating === "right" ? html`<div class="v-asm-mode-banner v-asm-mode-right"><span>➡ Annotating Right Window</span><span>Click the canvas to place points around the visible glass</span></div>`
          : state.error ? html`<div class="v-asm-mode-banner v-asm-mode-banner-error"><span>Snapshot unavailable</span><span>${state.error}</span><button class="v-asm-btn v-asm-btn-retry" @click="${retrySnapshot}">Retry</button></div>`
          : !state.image ? html`<div class="v-asm-mode-banner"><span>Loading camera snapshot...</span><span>The snapshot will load automatically</span></div>`
          : html`<div class="v-asm-mode-banner v-asm-mode-idle"><span>Idle Mode</span><span>Click "Annotate" above to configure your active canvas boundaries</span></div>`}

        <div class="v-asm-canvas-wrapper">
          <canvas id="v-asm-canvas" @click="${canvasClick}" @contextmenu="${canvasRightClick}"></canvas>
          <div class="v-asm-instructions">
            ${state.annotating ? "Click near the first point to close the polygon. Right-click to undo last point." : "Use the controls above to annotate each side's window area."}
          </div>
        </div>
      </div>

      <div class="v-asm-card v-asm-card-warning">
        <div class="v-asm-card-title">Sensitivity Settings</div>
        <ul class="v-asm-card-list">
          <li>Confidence Threshold: minimum confidence for a detection (higher means fewer false positives)</li>
          <li>Smoothing Duration: time constant for signal smoothing (higher means less flickering)</li>
          <li class="v-asm-card-action">Adjust these in <a href="/device_settings/lateral-steering">Toggles -> Lateral</a></li>
        </ul>
      </div>

      <div class="v-asm-section">
        <h3>Current Status</h3>
        <p class="v-asm-desc">Real-time V-ASM detection state from the daemon.</p>
        <div class="v-asm-status-grid">
          <div class="v-asm-status-card">
            <div class="v-asm-status-label">Left Active</div>
            <div class="v-asm-status-value" id="vasm-left-status">-</div>
          </div>
          <div class="v-asm-status-card">
            <div class="v-asm-status-label">Right Active</div>
            <div class="v-asm-status-value" id="vasm-right-status">-</div>
          </div>
          <div class="v-asm-status-card">
            <div class="v-asm-status-label">Left Confidence</div>
            <div class="v-asm-status-value" id="vasm-left-conf">-</div>
          </div>
          <div class="v-asm-status-card">
            <div class="v-asm-status-label">Right Confidence</div>
            <div class="v-asm-status-value" id="vasm-right-conf">-</div>
          </div>
        </div>
      </div>
    </div>
  `;

  scheduleInitialLoad();
  if (!window.__vasmPollStarted) {
    window.__vasmPollStarted = true;
    pollInterval = setInterval(async () => {
      try {
        const elLeft = document.getElementById("vasm-left-status");
        if (!elLeft) {
          if (pollHasBeenActive) {
            clearInterval(pollInterval);
            window.__vasmPollStarted = false;
            pollHasBeenActive = false;
          }
          return;
        }
        pollHasBeenActive = true;
        const keys = ["VASMLeftActive", "VASMRightActive", "VASMLeftConfidence", "VASMRightConfidence"];
        const results = {};
        for (const key of keys) {
          const resp = await fetch(`/api/params_memory?key=${encodeURIComponent(key)}`);
          if (resp.ok) results[key] = await resp.text();
        }
        const elRight = document.getElementById("vasm-right-status");
        const elLeftConf = document.getElementById("vasm-left-conf");
        const elRightConf = document.getElementById("vasm-right-conf");
        if (elLeft) {
          const active = results.VASMLeftActive === "1";
          elLeft.textContent = active ? "YES" : "no";
          elLeft.className = "v-asm-status-value " + (active ? "active" : "inactive");
        }
        if (elRight) {
          const active = results.VASMRightActive === "1";
          elRight.textContent = active ? "YES" : "no";
          elRight.className = "v-asm-status-value " + (active ? "active" : "inactive");
        }
        if (elLeftConf) elLeftConf.textContent = parseFloat(results.VASMLeftConfidence || "0").toFixed(3);
        if (elRightConf) elRightConf.textContent = parseFloat(results.VASMRightConfidence || "0").toFixed(3);
      } catch (e) {
      }
    }, 3000);
  }
  return el;
}