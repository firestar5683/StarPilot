"""Frozen V-ASM crop/side mapping with malformed and stale input boundaries."""

import json

import pytest

from openpilot.starpilot.spot_monitor.policy import (
  WarningPolicy, class_one_confidence, crop_for_side, decode_annotation, encode_annotation, polygon_pixels,
)


ONE_SIDE = {"version": 1, "width": 200, "height": 100,
            "poly_left": [[10, 10], [80, 10], [80, 80], [10, 80]], "poly_right": []}


def test_frozen_pixel_polygons_normalize_and_even_nv12_crop():
  annotation = decode_annotation(json.dumps(ONE_SIDE).encode())
  assert annotation.configured_sides == ("left",)
  assert annotation.camera_left is not None
  assert annotation.camera_left[0] == (0.05, 0.1)
  assert crop_for_side(annotation, "right", 200, 100) is None
  crop = crop_for_side(annotation, "left", 200, 100)
  assert (crop.x, crop.y, crop.width, crop.height) == (10, 10, 72, 72)
  assert (crop.model_width, crop.model_height, crop.pad_left, crop.pad_top) == (352, 352, 0, 0)
  doubled = crop_for_side(annotation, "left", 400, 200)
  assert (doubled.x, doubled.y, doubled.width, doubled.height) == (20, 20, 142, 142)
  assert decode_annotation(encode_annotation(annotation)) == annotation


def test_rectangular_crop_letterboxes_to_frozen_352_square():
  config = {"version": 1, "width": 200, "height": 100,
            "poly_left": [[10, 10], [110, 10], [110, 50], [10, 50]], "poly_right": []}
  crop = crop_for_side(decode_annotation(json.dumps(config)), "left", 200, 100)
  assert (crop.x, crop.y, crop.width, crop.height) == (10, 10, 102, 42)
  assert (crop.model_width, crop.model_height, crop.pad_left, crop.pad_top) == (352, 145, 0, 103)


def test_frozen_float32_pixel_projection_same_and_cross_resolution():
  config = {"version": 1, "width": 1928, "height": 1208,
            "poly_left": [[1609, 480], [1861, 480], [1861, 552], [1609, 552]], "poly_right": []}
  annotation = decode_annotation(json.dumps(config))
  assert polygon_pixels(annotation, "left", 1928, 1208)[0] == (1609, 480)
  same = crop_for_side(annotation, "left", 1928, 1208)
  assert (same.x, same.y, same.width, same.height) == (1608, 480, 254, 74)
  assert polygon_pixels(annotation, "left", 1344, 760)[0] == (1121, 301)
  scaled = crop_for_side(annotation, "left", 1344, 760)
  assert (scaled.x, scaled.y, scaled.width, scaled.height) == (1120, 300, 178, 48)

  config = {"version": 1, "width": 1344, "height": 760,
            "poly_left": [[448, 253], [635, 253], [635, 346], [448, 346]], "poly_right": []}
  annotation = decode_annotation(json.dumps(config))
  crop = crop_for_side(annotation, "left", 1344, 760)
  assert (crop.x, crop.y, crop.width, crop.height) == (448, 252, 188, 94)


@pytest.mark.parametrize("changed", [
  {"width": 0}, {"width": True}, {"width": 201}, {"poly_left": [[1, 1], [2, 2]]},
  {"poly_left": [[1, 1], [2, 2], [3, 3]]}, {"poly_left": [[1, 1], [2, 1], [2, float("nan")]]},
  {"poly_left": [[1, 1], [201, 1], [2, 2]]},
  {"poly_left": [[10, 10], [80, 80], [10, 80], [80, 10]]},
  {"poly_left": [[10, 10], [80, 10], [80, 80], [40, 10], [10, 80]]},
  {"poly_left": [[10, 10], [80, 10], [80, 80], [10, 80], [10, 10]]},
  {"version": True}, {"version": 2},
  {"poly_left": [], "poly_right": []},
])
def test_malformed_annotations_rejected(changed):
  with pytest.raises(ValueError):
    decode_annotation(json.dumps({**ONE_SIDE, **changed}))


def test_duplicate_unknown_oversized_and_nonfinite_json_rejected():
  for raw in (b'{"width":200,"width":200,"height":100,"poly_left":[],"poly_right":[]}',
              json.dumps({key: value for key, value in ONE_SIDE.items() if key != "version"}).encode(),
              json.dumps({**ONE_SIDE, "unknown": 1}).encode(),
              b" " * 8193,
              json.dumps(ONE_SIDE).replace("200", "NaN", 1).encode()):
    with pytest.raises(ValueError):
      decode_annotation(raw)


def test_class_one_and_camera_to_display_swap_with_hysteresis():
  assert class_one_confidence([0.05, 0.95, 0.0]) == 0.95
  assert class_one_confidence([0.2, 0.8]) == 0.8
  for malformed in ([0.9], [0.1, float("nan")], [0.1, 1.1], [], None):
    assert class_one_confidence(malformed) == 0.0
  policy = WarningPolicy(threshold=0.94, smooth_seconds=0.2)
  state = policy.update("left", [0.05, 0.95, 0.0], now=1.0, dt=0.5)
  assert (state.display_left, state.display_right) == (False, True)
  assert (state.display_left_confidence, state.display_right_confidence) == (0.0, 0.95)
  assert policy.update("left", [0.2, 0.8, 0.0], now=1.5, dt=0.5).display_right
  assert not policy.update("left", [0.22, 0.78, 0.0], now=2.0, dt=0.5).display_right
  assert policy.update("right", [0.04, 0.96, 0.0], now=2.5, dt=0.5).display_left
  assert not policy.update("left", [0.1, float("nan")], now=2.6, dt=0.5).display_left


def test_frozen_ema_and_per_side_freshness_fail_closed():
  policy = WarningPolicy(threshold=0.8, smooth_seconds=0.5)
  for index in range(1, 8):
    state = policy.update("left", [0.0, 1.0], now=index / 10, dt=0.1)
    assert not state.display_right
  state = policy.update("left", [0.0, 1.0], now=0.8, dt=0.1)
  assert state.display_right
  assert policy.score["left"] == pytest.approx(1 - 0.8**8)
  assert not policy.state(3.81).display_right
  # Fresh raw confidence after a gap must build the EMA again.
  assert not policy.update("left", [0.0, 1.0], now=4.0, dt=0.1).display_right
  assert not policy.update("left", [0.0, 1.0], now=4.0, dt=0.1).display_right
  assert not policy.update("left", [0.0, 1.0], now=4.1, dt=float("nan")).display_right


def test_disabled_or_clock_invalid_reset_never_retains_warning():
  policy = WarningPolicy()
  assert policy.update("right", [0.02, 0.98], now=1.0, dt=1.0).display_left
  policy.reset()
  assert not policy.state(1.1).display_left
  assert policy.update("right", [0.02, 0.98], now=2.0, dt=1.0).display_left
  assert not policy.update("right", [0.02, 0.98], now=1.9, dt=1.0).display_left
  with pytest.raises(ValueError):
    policy.update("middle", [0.02, 0.98], now=2.1, dt=1.0)


def test_reversed_status_clock_clears_history_without_resurrection():
  policy = WarningPolicy()
  assert policy.update("left", [0.02, 0.98], now=5.0, dt=1.0).display_right
  assert not policy.state(4.0).display_right
  assert not policy.state(5.1).display_right
