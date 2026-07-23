from __future__ import annotations
import time
from pathlib import Path
import cv2
import numpy as np
import onnxruntime as ort

_ASSETS = Path(__file__).resolve().parents[1] / "assets" / "vision_models"
V_ASM_MODEL_PATH = _ASSETS / "v_asm_model.onnx"

MODEL_INPUT_H = 256
MODEL_INPUT_W = 352
HYSTERESIS_ON = 0.65
HYSTERESIS_OFF = 0.25


class VASMInference:
  def __init__(self, model_path: Path):
    self.model_path = model_path
    self.session = None
    self._valid = False
    self.last_error = ""

    self.reset_state()

    self.frame_res = (0, 0)
    self.config_width = 0
    self.config_height = 0
    self.masks = {"left": None, "right": None}
    self.bboxes = {"left": None, "right": None, "left_raw": None, "right_raw": None}

  def load(self) -> bool:
    if not self.model_path.is_file():
      self.last_error = f"Missing model: {self.model_path}"
      self._valid = False
      return False
    try:
      opts = ort.SessionOptions()
      opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
      opts.intra_op_num_threads = 1
      opts.inter_op_num_threads = 1
      opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

      providers = ['CPUExecutionProvider']
      self.session = ort.InferenceSession(str(self.model_path), sess_options=opts, providers=providers)
      self.input_name = self.session.get_inputs()[0].name
      self.output_name = self.session.get_outputs()[0].name

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

  def _prepare_geometry(self, h, w):
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

      bx = (bx // 2) * 2
      by = (by // 2) * 2
      bw = ((bw + 1) // 2) * 2
      bh = ((bh + 1) // 2) * 2

      bx = max(0, min(bx, w - 2))
      by = max(0, min(by, h - 2))
      bw = max(2, min(bw, w - bx))
      bh = max(2, min(bh, h - by))

      bw = (bw // 2) * 2
      bh = (bh // 2) * 2

      self.bboxes[side] = (bx, by, bw, bh)

      mask = np.zeros((bh, bw), dtype=np.uint8)
      cv2.fillPoly(mask, [pts.astype(np.int32) - [bx, by]], 255)
      self.masks[side] = mask

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

  def _run_inference(self, raw_image, height, side):
    bbox = self.bboxes[side]
    if bbox is None or self.session is None:
      return 0.0

    x, y, w, h = bbox

    # Slice NV12 directly
    y_crop = raw_image[y: y + h, x: x + w]
    uv_crop = raw_image[height + y // 2: height + (y + h) // 2, x: x + w]
    nv12_crop = np.vstack([y_crop, uv_crop])

    # Convert cropped area directly from YUV NV12 to RGB (1-step, avoids double conversion)
    crop_rgb = cv2.cvtColor(nv12_crop, cv2.COLOR_YUV2RGB_NV12)
    if self.masks[side] is not None:
      crop_rgb = cv2.bitwise_and(crop_rgb, crop_rgb, mask=self.masks[side])

    # Preprocess -> NCHW Float32 [0.0 - 1.0]
    resized = cv2.resize(crop_rgb, (MODEL_INPUT_W, MODEL_INPUT_H), interpolation=cv2.INTER_LINEAR)
    blob = resized.astype(np.float32) / 255.0
    blob = np.transpose(blob, (2, 0, 1))
    blob = np.expand_dims(blob, axis=0)

    # Run inference via ONNX Runtime
    out = self.session.run([self.output_name], {self.input_name: blob})[0]

    preds = np.squeeze(out)
    if preds.ndim == 2:
      if preds.shape[0] < preds.shape[1]:
        preds = preds.T
      if preds.shape[1] >= 6:
        is_class_0 = (np.round(preds[:, 5]).astype(int) == 0)
        relevant = preds[is_class_0]
        if len(relevant) == 0:
          return 0.0
        return float(np.max(relevant[:, 4]))
      elif preds.shape[1] >= 5:
        return float(np.max(preds[:, 4]))
      else:
        return float(np.max(preds[:, 0]))
    elif preds.ndim == 1 and preds.size > 0:
      return float(np.max(preds))
    return 0.0

  def update(self, raw_image, width, height, dt, conf_thresh, smooth_sec, side_to_infer):
    if not self._valid:
      return False, False

    self._prepare_geometry(height, width)
    alpha = min(1.0, dt / max(smooth_sec, 0.001))

    raw_conf = self._run_inference(raw_image, height, side_to_infer)
    if side_to_infer == "left":
      if raw_conf >= conf_thresh:
        self._l_score = min(1.0, self._l_score + alpha)
      else:
        self._l_score = max(0.0, self._l_score - alpha)
      self.left_confidence = raw_conf
      if self._l_score >= HYSTERESIS_ON:
        self.left_active = True
      elif self._l_score <= HYSTERESIS_OFF:
        self.left_active = False
    else:
      if raw_conf >= conf_thresh:
        self._r_score = min(1.0, self._r_score + alpha)
      else:
        self._r_score = max(0.0, self._r_score - alpha)
      self.right_confidence = raw_conf
      if self._r_score >= HYSTERESIS_ON:
        self.right_active = True
      elif self._r_score <= HYSTERESIS_OFF:
        self.right_active = False

    return self.left_active, self.right_active