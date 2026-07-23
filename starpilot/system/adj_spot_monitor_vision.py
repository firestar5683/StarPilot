#!/usr/bin/env python3
from __future__ import annotations
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
import time
import cv2
import numpy as np
import cereal.messaging as messaging
from openpilot.common.params import Params
from openpilot.common.realtime import set_core_affinity, Ratekeeper
from openpilot.system.hardware import PC
from openpilot.starpilot.common.starpilot_utilities import device_cpu_throttle_factor
from openpilot.starpilot.system.adj_spot_monitor_vision_inference import VASMInference, V_ASM_MODEL_PATH

V_ASM_AFFINITY_CORES = [2]
V_ASM_SOLO_AFFINITY_CORES = [0, 1, 2]

BASE_INTERVAL = 0.500
FOLLOWUP_INTERVAL = 0.200
FOLLOWUP_WINDOW = 1.5

PARAM_REFRESH_INTERVAL = 2.0
STATUS_LOG_INTERVAL = 10.0


class VASMDaemon:
  def __init__(self):
    from msgq.visionipc import VisionIpcClient, VisionStreamType

    self.params = Params()
    self.params_memory = Params(memory=True)
    self.sm = messaging.SubMaster(["deviceState", "starpilotCarState", "managerState"])

    self.VisionIpcClient = VisionIpcClient
    self.stream_type = VisionStreamType.VISION_STREAM_DRIVER
    self.client = None

    self.inference = VASMInference(V_ASM_MODEL_PATH)
    self.inference.load()

    self._cache_params()

    self.last_inference_at = 0.0
    self.last_inference_at_side = {"left": 0.0, "right": 0.0}
    self.current_side = "left"

    self.followup_until = 0.0
    self.onroad_prev = False

    self._last_pub_left = False
    self._last_pub_right = False
    self._last_pub_left_conf = -1.0
    self._last_pub_right_conf = -1.0
    self._last_param_refresh = 0.0
    self._throttle_reason = "none"
    self._last_status_log = 0.0
    self._inference_count = 0

    self._affinity_set = False
    self._prev_other_running = None

    self.params.put("VASMLeftActive", "0")
    self.params.put("VASMRightActive", "0")
    self.params.put("VASMLeftConfidence", "0.0")
    self.params.put("VASMRightConfidence", "0.0")
    self.params.put("VASMTimestampEof", "0")

    self._annotation_loaded = False
    self._load_annotation_config()

    print(f"[VASM] Started (model_valid={self.inference.valid})")

  def _cache_params(self):
    self._enabled = self.params.get_bool("VASMEnabled")
    self._conf_thresh = self.params.get_float("VASMConfidenceThreshold")
    self._smooth_sec = self.params.get_float("VASMSmoothSeconds")

  def _maybe_refresh_params(self, now):
    if now - self._last_param_refresh >= PARAM_REFRESH_INTERVAL:
      self._last_param_refresh = now
      self._enabled = self.params.get_bool("VASMEnabled")
      self._conf_thresh = self.params.get_float("VASMConfidenceThreshold")
      self._smooth_sec = self.params.get_float("VASMSmoothSeconds")
      if not self._annotation_loaded:
        self._load_annotation_config()

  def _load_annotation_config(self):
    try:
      config = self.params.get("VASMAnnotationConfig")
      if config:
        has_left = bool(config.get("poly_left"))
        has_right = bool(config.get("poly_right"))
        if has_left or has_right:
          self.inference.load_config(config)
          self._annotation_loaded = True
          sides = []
          if has_left: sides.append("left")
          if has_right: sides.append("right")
          print(f"[VASM] Annotation config loaded (sides: {', '.join(sides)})")
          return
    except Exception:
      pass
    self._annotation_loaded = False
    print("[VASM] No annotation config found  inference disabled until annotated via Galaxy")

  def _connect_camera(self):
    if self.client is not None and self.client.is_connected():
      return True
    try:
      available = self.VisionIpcClient.available_streams("camerad", block=False)
    except Exception:
      available = []

    if self.stream_type not in available:
      return False

    if self.client is None:
      self.client = self.VisionIpcClient("camerad", self.stream_type, True)

    if not self.client.is_connected():
      self.client.connect(True)
    return self.client.is_connected()

  def _update_inactive(self, reset_inference=False):
    if reset_inference:
      self.inference.reset_state()
    if self._last_pub_left or self._last_pub_right or self._last_pub_left_conf != 0.0 or self._last_pub_right_conf != 0.0:
      self._publish(False, False, 0.0, 0.0, 0, force=True)

  def _inference_interval(self, now):
    in_followup = now < self.followup_until
    base = FOLLOWUP_INTERVAL if in_followup else BASE_INTERVAL
    cpu_usage = list(self.sm["deviceState"].cpuUsagePercent) if self.sm.valid.get("deviceState", False) else []
    factor = device_cpu_throttle_factor(cpu_usage, name="VASM")
    interval = base * factor
    self._throttle_reason = f"cpu_{factor:.1f}x" if factor > 1.05 else ("followup" if in_followup else "steady")
    return interval

  def _other_daemon_running(self):
    if not self.sm.valid.get("managerState", False):
      return False
    return any(p.name == "speed_limit_vision" and p.running for p in self.sm["managerState"].processes)

  def _update_core_affinity(self, now):
    other_running = self._other_daemon_running()
    if other_running != self._prev_other_running:
      self._affinity_set = False
      self._prev_other_running = other_running
    if not self._affinity_set:
      set_core_affinity(V_ASM_AFFINITY_CORES if other_running else V_ASM_SOLO_AFFINITY_CORES)
      self._affinity_set = True

  def run(self):
    rk = Ratekeeper(10, None)

    while True:
      try:
        now = time.monotonic()
        self._maybe_refresh_params(now)
        self.sm.update(0)

        if not PC:
          self._update_core_affinity(now)
        onroad = self.sm["deviceState"].started if self.sm.valid.get("deviceState", False) else False
        parked = self.sm["starpilotCarState"].isParked if self.sm.valid.get("starpilotCarState", False) else False

        if not onroad or not self._enabled or not self.inference.valid or not self._annotation_loaded:
          self._update_inactive(reset_inference=(onroad != self.onroad_prev))
          if onroad != self.onroad_prev:
            self.last_inference_at = 0.0
          self.onroad_prev = onroad
          if now - self._last_status_log >= STATUS_LOG_INTERVAL and not onroad:
            cpu = list(self.sm["deviceState"].cpuUsagePercent) if self.sm.valid.get("deviceState", False) else []
            cpu_str = f"avg={sum(cpu)/len(cpu):.0f}% cores={','.join(f'{c:.0f}' for c in cpu)}" if cpu else "?"
            print(f"[VASM] idle | {cpu_str} | onroad={onroad} parked={parked} enabled={self._enabled} model={self.inference.valid} ann={self._annotation_loaded}")
            self._last_status_log = now
          rk.keep_time()
          continue

        self.onroad_prev = onroad

        if not self._connect_camera():
          rk.keep_time()
          continue

        inference_interval = self._inference_interval(now)

        if self.last_inference_at != 0.0 and (now - self.last_inference_at < inference_interval - 0.015):
          self._publish(self.inference.left_active, self.inference.right_active,
                        self.inference.left_confidence, self.inference.right_confidence,
                        int(self.client.timestamp_sof))
          rk.keep_time()
          continue

        buffer = None
        while True:
          b = self.client.recv(timeout_ms=0)
          if b is None:
            break
          buffer = b

        if buffer is None:
          rk.keep_time()
          continue

        last_side_time = self.last_inference_at_side[self.current_side]
        dt = (now - last_side_time) if last_side_time != 0.0 else inference_interval

        self.last_inference_at = now
        self.last_inference_at_side[self.current_side] = now

        image = np.frombuffer(buffer.data, dtype=np.uint8).reshape(
          (len(buffer.data) // self.client.stride, self.client.stride)
        )

        if self.client.stride != self.client.width:
          image = image[:, :self.client.width]

        l_active, r_active = self.inference.update(
          image,
          self.client.width,
          self.client.height,
          dt=dt,
          conf_thresh=self._conf_thresh,
          smooth_sec=self._smooth_sec,
          side_to_infer=self.current_side,
        )

        self._inference_count += 1
        if now - self._last_status_log >= STATUS_LOG_INTERVAL:
          self._last_status_log = now
          cpu = list(self.sm["deviceState"].cpuUsagePercent) if self.sm.valid.get("deviceState", False) else []
          cpu_str = f"avg={sum(cpu)/len(cpu):.0f}% cores={','.join(f'{c:.0f}' for c in cpu)}" if cpu else "?"
          factor = device_cpu_throttle_factor(cpu)
          print(f"[VASM] {self._inference_count} inf {self._throttle_reason} | {cpu_str} | factor={factor:.1f}x | L={self.inference.left_confidence:.3f} R={self.inference.right_confidence:.3f}")
          self._inference_count = 0

        self._publish(l_active, r_active, self.inference.left_confidence,
                      self.inference.right_confidence, int(self.client.timestamp_sof))

        if l_active or r_active:
          self.followup_until = now + FOLLOWUP_WINDOW

        self.current_side = "right" if self.current_side == "left" else "left"

        rk.keep_time()

      except Exception as e:
        print(f"VASM Daemon Error: {e}")
        time.sleep(1.0)

  def _publish(self, left_active, right_active, left_conf, right_conf, ts_sof, force=False):
    r_left_conf = round(left_conf, 3)
    r_right_conf = round(right_conf, 3)

    if not force and \
       left_active == self._last_pub_left and \
       right_active == self._last_pub_right and \
       abs(r_left_conf - self._last_pub_left_conf) < 0.005 and \
       abs(r_right_conf - self._last_pub_right_conf) < 0.005:
      return

    self._last_pub_left = left_active
    self._last_pub_right = right_active
    self._last_pub_left_conf = r_left_conf
    self._last_pub_right_conf = r_right_conf

    ui_left_active, ui_right_active = right_active, left_active
    ui_left_conf, ui_right_conf = right_conf, left_conf

    self.params_memory.put("VASMLeftActive", "1" if ui_left_active else "0")
    self.params_memory.put("VASMRightActive", "1" if ui_right_active else "0")
    self.params_memory.put("VASMLeftConfidence", str(ui_left_conf))
    self.params_memory.put("VASMRightConfidence", str(ui_right_conf))
    self.params_memory.put("VASMTimestampEof", str(ts_sof))


def main():
  cv2.setNumThreads(1)
  VASMDaemon().run()


if __name__ == "__main__":
  main()