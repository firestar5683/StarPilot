from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np

_ASSETS = Path(__file__).resolve().parents[1] / "assets" / "vision_models"
V_ASM_MODEL_PATH = _ASSETS / "v_asm_model.onnx"

MODEL_INPUT_SIZE = 352


class VASMInference:
  def __init__(self, model_path: Path):
    self.model_path = model_path
    self.net = None
    self._valid = False
    self.last_error = ""

    self.reset_state()

    self.frame_res = (0, 0)
    self.config_width = 0
    self.config_height = 0
    self.masks = {"left": None, "right": None}
    self.bboxes = {
        "left": None,
        "right": None,
        "left_raw": None,
        "right_raw": None,
    }

  def load(self) -> bool:
    if not self.model_path.is_file():
      self.last_error = f"Missing model: {self.model_path}"
      self._valid = False
      return False
    try:
      self.net = cv2.dnn.readNetFromONNX(str(self.model_path))
      self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
      self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
      self._valid = True
      self.last_error = ""
    except Exception as e:
      self.last_error = f"Failed to load model: {e}"
      self._valid = False
    return self._valid

  def reset_state(self):
    self._l_score = 0.0
    self._r_score = 0.0
    self.left_active = False
    self.right_active = False
    self.left_confidence = 0.0
    self.right_confidence = 0.0

  @property
  def valid(self):
    return self._valid

  @property
  def configured_sides(self):
    return tuple(
        side
        for side in ("left", "right")
        if self.bboxes.get(f"{side}_raw") is not None
    )

  def load_config(self, config: dict):
    self.frame_res = (0, 0)
    self.config_width = config.get("width", 0)
    self.config_height = config.get("height", 0)

    for side in ("left", "right"):
      poly = config.get(f"poly_{side}", [])
      if len(poly) >= 3:
        self.bboxes[f"{side}_raw"] = np.array(poly, dtype=np.float32)
      else:
        self.bboxes[f"{side}_raw"] = None
        self.bboxes[side] = None

  def _prepare_geometry(self, h: int, w: int):
    if (h, w) == self.frame_res:
      return
    self.frame_res = (h, w)

    scale_x = w / float(self.config_width) if self.config_width > 0 else 1.0
    scale_y = h / float(self.config_height) if self.config_height > 0 else 1.0

    for side in ("left", "right"):
      raw_pts = self.bboxes.get(f"{side}_raw")
      if raw_pts is None:
        self.bboxes[side] = None
        self.masks[side] = None
        continue

      pts = raw_pts.copy()
      pts[:, 0] *= scale_x
      pts[:, 1] *= scale_y

      bx, by, bw, bh = cv2.boundingRect(pts.astype(np.int32))

      bx = max(0, min((bx // 2) * 2, w - 2))
      by = max(0, min((by // 2) * 2, h - 2))
      bw = max(2, min(((bw + 1) // 2) * 2, w - bx))
      bh = max(2, min(((bh + 1) // 2) * 2, h - by))

      bw = (bw // 2) * 2
      bh = (bh // 2) * 2

      self.bboxes[side] = (bx, by, bw, bh)

      mask = np.zeros((bh, bw), dtype=np.uint8)
      cv2.fillPoly(mask, [pts.astype(np.int32) - [bx, by]], 255)
      self.masks[side] = mask

  def _run_inference(self, raw_image: np.ndarray, height: int, side: str) -> float:
    bbox = self.bboxes[side]
    if bbox is None or self.net is None:
      return 0.0

    x, y, w, h = bbox

    y_crop = raw_image[y : y + h, x : x + w]
    uv_crop = raw_image[height + y // 2 : height + (y + h) // 2, x : x + w]
    nv12_crop = np.vstack([y_crop, uv_crop])

    crop_rgb = cv2.cvtColor(nv12_crop, cv2.COLOR_YUV2RGB_NV12)
    if self.masks[side] is not None:
      crop_rgb = cv2.bitwise_and(crop_rgb, crop_rgb, mask=self.masks[side])

    rs = MODEL_INPUT_SIZE
    ch, cw = crop_rgb.shape[:2]
    scale = rs / float(max(ch, cw))
    nh, nw = int(round(ch * scale)), int(round(cw * scale))
    resized = cv2.resize(crop_rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)

    crop_sq = np.zeros((rs, rs, 3), dtype=np.uint8)
    top = (rs - nh) // 2
    left = (rs - nw) // 2
    crop_sq[top : top + nh, left : left + nw] = resized

    blob = crop_sq.astype(np.float32) / 255.0
    blob = np.transpose(blob, (2, 0, 1))
    blob = np.expand_dims(blob, axis=0)

    self.net.setInput(blob)
    out = self.net.forward()

    preds = np.squeeze(out)

    # Direct output for Class 1 ('1_car' blindspot threat in tri-class model)
    if preds.ndim >= 1 and preds.size > 0:
      return float(preds[1]) if len(preds) > 1 else float(preds[0])

    return 0.0

  def update(
      self,
      raw_image: np.ndarray,
      width: int,
      height: int,
      dt: float,
      conf_thresh: float,
      smooth_sec: float,
      side_to_infer: str,
      conf_hold_off: float | None = None,
  ) -> tuple[bool, bool]:
    if not self._valid:
      return False, False

    if conf_hold_off is None:
      conf_hold_off = max(0.0, conf_thresh - 0.15)

    self._prepare_geometry(height, width)
    alpha = min(1.0, dt / max(smooth_sec, 0.001))

    raw_conf = self._run_inference(raw_image, height, side_to_infer)

    if side_to_infer == "left":
      self.left_confidence = raw_conf
      # Exponential Moving Average Smoothing
      self._l_score = (1.0 - alpha) * self._l_score + alpha * raw_conf

      # Dual-Threshold Hysteresis Logic
      if not self.left_active:
        if self._l_score >= conf_thresh:
          self.left_active = True
      else:
        if self._l_score < conf_hold_off:
          self.left_active = False

    else:
      self.right_confidence = raw_conf
      self._r_score = (1.0 - alpha) * self._r_score + alpha * raw_conf

      if not self.right_active:
        if self._r_score >= conf_thresh:
          self.right_active = True
      else:
        if self._r_score < conf_hold_off:
          self.right_active = False

    return self.left_active, self.right_active