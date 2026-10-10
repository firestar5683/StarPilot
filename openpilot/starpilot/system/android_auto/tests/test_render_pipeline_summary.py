from openpilot.starpilot.system.android_auto.render_profile import RenderPipelineSummary


def test_gpu_completion_is_not_confused_with_submission_or_camera_eof():
  summary = RenderPipelineSummary(0, interval_ns=50_000_000)
  assert summary.published(10_000_000, 21_000_000, 49_000_000, (0, 1, 1_000_000)) is None
  report = summary.published(60_000_000, 71_000_000, 101_000_000, (0, 2, 51_000_000))
  assert report['capture_to_submit_p95_ms'] == 11
  assert report['submit_to_publish_p95_ms'] == 30
  assert report['capture_to_publish_p95_ms'] == 41
  assert report['camera_eof_to_publish_p95_ms'] == 50
  assert report['published_frames'] == 2
  assert report['camera_id_repeats'] == report['camera_id_gaps'] == 0


def test_stream_switch_reset_and_offroad_do_not_look_like_camera_drops():
  summary = RenderPipelineSummary(0, interval_ns=100)
  for frame, camera in enumerate(((0, 1, 1), (0, 1, 1), (0, 4, 2), (2, 400, 3), (2, 1, 4), None, (2, 90, 6))):
    assert summary.published(frame * 10, frame * 10 + 1, frame * 10 + 2, camera) is None
  report = summary.published(100, 101, 102)
  assert report['camera_id_repeats'] == 1
  assert report['camera_id_gaps'] == 2
  assert report['camera_id_resets'] == 1
  report = summary.published(200, 201, 202)
  assert report['published_frames'] == 1
  assert report['camera_eof_to_publish_p95_ms'] is None
  assert report['camera_id_repeats'] == report['camera_id_gaps'] == 0


def test_storage_is_bounded_and_bad_clock_samples_are_ignored():
  summary = RenderPipelineSummary(0, interval_ns=10_000)
  assert summary.published(3, 2, 4) is None
  assert summary.frames == 0
  for frame in range(1000):
    summary.published(frame, frame + 1, frame + 2, (0, frame, frame + 100))
  assert len(summary.samples) == 240
  assert summary.frames == 1000
  assert all(sample[3] is None for sample in summary.samples)
