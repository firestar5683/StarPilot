"""Native-free contract for Small lane/edge projection; no renderer lifecycle is bypassed."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import warnings

import numpy as np
import pytest


def current():
  source = Path(__file__).parents[3] / "selfdrive/ui/mici/onroad/model_renderer.py"
  node = next(n for n in ast.walk(ast.parse(source.read_text()))
              if isinstance(n, ast.FunctionDef) and n.name == "_map_lines_to_polygons")
  namespace = {"np": np}
  exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"), namespace)
  return namespace[node.name]


def reference(self, lines: list[np.ndarray], widths: list[float], max_idx: int) -> list[np.ndarray]:
  """Project clipped lane/edge pairs together while preserving per-line masks."""
  points = [line[:max_idx + 1][line[:max_idx + 1, 0] >= 0] for line in lines]
  counts = [len(line) for line in points]
  total = sum(counts)
  if total == 0:
    return [np.empty((0, 2), dtype=np.float32) for _ in lines]
  offsets = np.zeros((2, total, 3), dtype=np.float32)
  offsets[1, :, 1] = np.repeat(widths, counts)
  offsets[0, :, 1] = -offsets[1, :, 1]
  joined = np.concatenate(points)
  proj = (self._car_space_transform @ (joined[None, :, :] + offsets).reshape(2 * total, 3).T).reshape(3, 2, total)
  valid = (np.abs(proj[2, 0]) >= 1e-06) & (np.abs(proj[2, 1]) >= 1e-06)
  polygons = []
  start = 0
  clip = self._clip_region
  for count in counts:
    end = start + count
    local = proj[:, :, start:end][:, :, valid[start:end]]
    if local.shape[2] == 0:
      polygons.append(np.empty((0, 2), dtype=np.float32))
      start = end
      continue
    left = local[:2, 0] / local[2, 0][None, :]
    right = local[:2, 1] / local[2, 1][None, :]
    keep = ((left[0] >= clip.x) & (left[0] <= clip.x + clip.width) &
        (left[1] >= clip.y) & (left[1] <= clip.y + clip.height) &
        (right[0] >= clip.x) & (right[0] <= clip.x + clip.width) &
        (right[1] >= clip.y) & (right[1] <= clip.y + clip.height))
    left, right = (left[:, keep], right[:, keep])
    polygons.append(np.vstack((left.T, right[:, ::-1].T)).astype(np.float32) if left.shape[1] else np.empty((0, 2), dtype=np.float32))
    start = end
  return polygons


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
def test_projection_exact_edges_and_live_mutation(dtype):
  rng = np.random.default_rng(3921)
  function = current()
  owner = NS(_car_space_transform=np.array([[580, -480, 0], [400, 0, -480], [1, 0, 0]], dtype=dtype),
             _clip_region=NS(x=-500, y=-500, width=1536, height=1240))
  for index in range(240):
    lines = [rng.normal(size=(33, 3)).astype(dtype) for _ in range(6)]
    for line in lines:
      line[:, 0] = np.linspace(-2, 100, 33)
    lines[0][:8, 0] = [-0., 0., 1e-7, 1e-6, np.nextafter(dtype(1e-6), dtype(0)), np.inf, np.nan, 1.]
    lines[1][4:7, 1] = [np.nan, np.inf, -np.inf]
    if index % 7 == 0:
      lines[index % 6] = lines[index % 6][:0]
    widths = [.12, .16, .16, .16, .16, .16]
    original = [line.copy() for line in lines]
    with np.errstate(all="ignore"):
      expected = reference(owner, lines, widths, index % 33)
      actual = function(owner, lines, widths, index % 33)
    for left, right in zip(expected, actual, strict=True):
      assert left.dtype == right.dtype == np.float32
      assert left.tobytes() == right.tobytes()
      assert not any(np.shares_memory(right, line) for line in lines)
    for old, line in zip(original, lines, strict=True):
      np.testing.assert_array_equal(old, line)
    for i, polygon in enumerate(actual):
      assert not any(np.shares_memory(polygon, other) for other in actual[i + 1:])
    # Rect and transform are deliberately changed every call, never cached.
    owner._clip_region.x = (index % 5) * 100 - 500
    owner._car_space_transform[0, 0] += dtype(.1)


def test_clip_inclusive_and_outputs_are_independent():
  owner = NS(_car_space_transform=np.eye(3, dtype=np.float32), _clip_region=NS(x=0, y=0, width=1, height=1))
  line = np.array([[0, 0, 1], [1, 1, 1], [np.nextafter(np.float32(1), np.float32(2)), 1, 1]], np.float32)
  fn = current()
  result = fn(owner, [line, line], [0, 0], 2)
  assert result[0].tolist() == [[0, 0], [1, 1], [1, 1], [0, 0]]
  result[0][:] = 99
  assert result[1][0].tolist() == [0, 0]
  line[0, 0] = .5
  assert fn(owner, [line], [0], 2)[0][0, 0] == .5


@pytest.mark.parametrize("lines,widths,index", [([], [], 0), ([np.empty((0, 3))], [], 0),
  ([np.ones((2, 3))], [], 1), ([np.ones((2, 3))], [1, 2], 1),
  ([np.ones((2, 2))], [1], 1), ([np.ones((2, 3))], [1], -1)])
def test_empty_and_invalid_input_contract(lines, widths, index):
  owner = NS(_car_space_transform=np.eye(3, dtype=np.float32), _clip_region=NS(x=-10, y=-10, width=20, height=20))
  outcomes = []
  for fn in (reference, current()):
    with warnings.catch_warnings(record=True) as caught:
      warnings.simplefilter("always")
      try:
        result = fn(owner, lines, widths, index)
        outcome = [x.tobytes() for x in result]
      except Exception as error:
        outcome = (type(error), str(error))
      outcomes.append((outcome, [(type(x.message), str(x.message)) for x in caught]))
  assert outcomes[0] == outcomes[1]
