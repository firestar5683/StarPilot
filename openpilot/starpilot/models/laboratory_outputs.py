from typing import Any

import numpy as np


LATERAL_PLAN_COLUMNS = (1, 4, 7, 11, 14)
LATERAL_OUTPUT_KEYS = (
  "desired_curvature", "desired_curvature_stds", "lat_planner_solution", "lat_planner_solution_stds",
  "lane_lines", "lane_lines_stds", "lane_lines_prob", "road_edges", "road_edges_stds", "desire_state", "desire_pred",
)
CURRENT_FRAME_OUTPUT_KEYS = (
  "pose", "pose_stds", "wide_from_device_euler", "wide_from_device_euler_stds", "road_transform", "road_transform_stds",
)


def _validate_outputs(outputs: dict[str, np.ndarray]) -> None:
  for key, value in outputs.items():
    if not isinstance(value, np.ndarray) or not np.isfinite(value).all():
      raise ValueError(f"Model Laboratory requires finite normalized arrays: {key}")


def _merge_plan(lateral: np.ndarray, longitudinal: np.ndarray) -> np.ndarray:
  if lateral.shape != longitudinal.shape or lateral.ndim < 2 or lateral.shape[-1] < 15:
    raise ValueError(f"Model Laboratory incompatible plan shapes: {lateral.shape}, {longitudinal.shape}")
  merged = longitudinal.copy()
  merged[..., LATERAL_PLAN_COLUMNS] = lateral[..., LATERAL_PLAN_COLUMNS]
  return merged


def compose_model_outputs(lateral_output: dict[str, np.ndarray], longitudinal_output: dict[str, np.ndarray],
                          current_frame_output: dict[str, np.ndarray] | None = None) -> dict[str, np.ndarray]:
  """Own lateral plan/geometry and longitudinal extras; decode actions separately per generation."""
  frame_output = longitudinal_output if current_frame_output is None else current_frame_output
  for outputs in (lateral_output, longitudinal_output, frame_output):
    _validate_outputs(outputs)
  if "plan" not in lateral_output or "plan" not in longitudinal_output:
    raise ValueError("Model Laboratory requires a plan from both models")
  if ("plan_stds" in lateral_output) != ("plan_stds" in longitudinal_output):
    raise ValueError("Model Laboratory requires matching plan uncertainty outputs")

  composed = {key: value.copy() for key, value in longitudinal_output.items() if key not in ("action", "action_stds")}
  composed["plan"] = _merge_plan(lateral_output["plan"], longitudinal_output["plan"])
  if "plan_stds" in lateral_output:
    composed["plan_stds"] = _merge_plan(lateral_output["plan_stds"], longitudinal_output["plan_stds"])
  for keys, outputs in ((LATERAL_OUTPUT_KEYS, lateral_output), (CURRENT_FRAME_OUTPUT_KEYS, frame_output)):
    for key in keys:
      if key in outputs:
        composed[key] = outputs[key].copy()
      else:
        composed.pop(key, None)
  return composed


def hybrid_action_values(lateral_action: Any, longitudinal_action: Any) -> dict[str, Any]:
  """Accept already decoded actions, never raw generation-dependent action tensors."""
  curvature = float(lateral_action.desiredCurvature)
  acceleration = float(longitudinal_action.desiredAcceleration)
  if not np.isfinite((curvature, acceleration)).all():
    raise ValueError("Model Laboratory requires finite decoded actions")
  return {"desiredCurvature": curvature, "desiredAcceleration": acceleration, "shouldStop": bool(longitudinal_action.shouldStop)}
