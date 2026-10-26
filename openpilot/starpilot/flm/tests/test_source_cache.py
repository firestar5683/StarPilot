"""Settings reads stay at receipt-renewal rate whatever the snapshot says."""

from openpilot.starpilot.flm import steerlearnerd
from openpilot.starpilot.flm.runtime_adapter_registry import SOURCE_LEASE_NS, SourceState

GENERATION = 'a' * 32
NEXT_GENERATION = 'b' * 32
MS = 1_000_000


def snapshot(now, *, enabled=True, generation=GENERATION):
  # Off, manual and unreadable snapshots are built without a calibration generation.
  return SourceState(enabled, False, '0', 'e' * 64 if enabled else '', now, now + SOURCE_LEASE_NS, 'c' * 64,
                     calibration_generation=generation if enabled else '')


def cache(frames, **kwargs):
  reads = []

  def read(now, frame):
    reads.append((now, frame))
    return snapshot(now, **kwargs)
  return steerlearnerd._SourceCache(read, lambda now: frames[0]), reads


def test_off_snapshot_with_current_calibration_is_reused_until_renewal():
  frames = [(GENERATION, (0., 0., 0.))]
  source, reads = cache(frames, enabled=False)
  for step in range(25):  # 100 Hz for 240 ms
    assert not source.read(1_000 * MS + step * 10 * MS).enabled
  assert len(reads) == 1
  source.read(1_250 * MS)
  assert len(reads) == 2


def test_enabled_snapshot_is_reused_until_renewal():
  frames = [(GENERATION, (0., 0., 0.))]
  source, reads = cache(frames)
  for step in range(25):
    source.read(1_000 * MS + step * 10 * MS)
  assert len(reads) == 1


def test_calibration_generation_change_reads_at_once():
  frames = [(GENERATION, (0., 0., 0.))]
  source, reads = cache(frames, enabled=False)
  source.read(1_000 * MS)
  frames[0] = (NEXT_GENERATION, (0., 0., 0.))
  source.read(1_010 * MS)
  frames[0] = None
  source.read(1_020 * MS)
  source.read(1_030 * MS)
  assert [frame for _, frame in reads] == [(GENERATION, (0., 0., 0.)), (NEXT_GENERATION, (0., 0., 0.)), None]


def test_publication_always_reads_and_renews_the_cache():
  frames = [(GENERATION, (0., 0., 0.))]
  source, reads = cache(frames, enabled=False)
  source.read(1_000 * MS)
  published = source.read_now(1_100 * MS)
  assert len(reads) == 2
  assert source.read(1_300 * MS) is published  # renewed at 1.1 s, still inside the 250 ms window
  assert len(reads) == 2
