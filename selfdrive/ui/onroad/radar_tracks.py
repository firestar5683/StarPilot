import numpy as np


def project_radar_points(
  d_rel: np.ndarray,
  in_y: np.ndarray,
  path_x: np.ndarray,
  path_z: np.ndarray,
  transform: np.ndarray,
  path_offset_z: float,
  clip_bounds: tuple[float, float, float, float],
  rect_bounds: tuple[float, float, float, float],
) -> np.ndarray:
  """Project radar points into screen space, preserving source order."""
  if d_rel.size == 0 or path_x.size == 0:
    return np.empty((0, 2), dtype=np.float64)

  finite = np.isfinite(d_rel) & np.isfinite(in_y)
  if not np.any(finite):
    return np.empty((0, 2), dtype=np.float64)

  d_rel = d_rel[finite]
  in_y = in_y[finite]

  path_indices = np.searchsorted(path_x, d_rel, side="right") - 1
  path_indices = np.maximum(path_indices, 0)

  line_z = np.zeros(d_rel.shape, dtype=np.float64)
  valid_z = path_indices < path_z.size
  if np.any(valid_z):
    line_z[valid_z] = path_z[path_indices[valid_z]]

  in_z = line_z + float(path_offset_z)

  # The former scalar implementation converts float32 matrix values to Python
  # floats before arithmetic. Keep this path in float64 to preserve its
  # screen-coordinate and boundary behavior.
  t = transform.astype(np.float64, copy=False)
  point_w = t[2, 0] * d_rel + t[2, 1] * in_y + t[2, 2] * in_z
  valid_w = np.abs(point_w) >= 1e-6

  x = np.zeros_like(d_rel)
  y = np.zeros_like(d_rel)
  x_num = t[0, 0] * d_rel + t[0, 1] * in_y + t[0, 2] * in_z
  y_num = t[1, 0] * d_rel + t[1, 1] * in_y + t[1, 2] * in_z
  np.divide(x_num, point_w, out=x, where=valid_w)
  np.divide(y_num, point_w, out=y, where=valid_w)

  clip_x, clip_y, clip_xmax, clip_ymax = clip_bounds
  visible = (
    valid_w
    & (x >= clip_x) & (x <= clip_xmax)
    & (y >= clip_y) & (y <= clip_ymax)
  )
  if not np.any(visible):
    return np.empty((0, 2), dtype=np.float64)

  rect_x, rect_y, rect_xmax, rect_ymax = rect_bounds
  return np.column_stack((
    np.clip(x[visible], rect_x, rect_xmax),
    np.clip(y[visible], rect_y, rect_ymax),
  ))
