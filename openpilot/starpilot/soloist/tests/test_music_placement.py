from pathlib import Path

import pytest

from openpilot.starpilot.soloist import supervisor


class FakeScheduler:
  def __init__(self, affinity, nice):
    self.affinity, self.nice = dict(affinity), dict(nice)
    self.pinned, self.reniced = [], []

  def install(self, monkeypatch):
    monkeypatch.setattr(supervisor.sys, 'platform', 'linux')
    monkeypatch.setattr(supervisor.os, 'sched_getaffinity', self.get_affinity, raising=False)
    monkeypatch.setattr(supervisor.os, 'sched_setaffinity', self.set_affinity, raising=False)
    monkeypatch.setattr(supervisor.os, 'getpriority', lambda _which, tid: self.nice[tid])
    monkeypatch.setattr(supervisor.os, 'setpriority', self.set_nice)

  def get_affinity(self, tid):
    if tid not in self.affinity:
      raise ProcessLookupError(tid)
    return self.affinity[tid]

  def set_affinity(self, tid, cores):
    if tid not in self.affinity:
      raise ProcessLookupError(tid)
    self.affinity[tid] = set(cores)
    self.pinned.append(tid)

  def set_nice(self, _which, tid, nice):
    self.nice[tid] = nice
    self.reniced.append(tid)


def tasks(root: Path, threads: dict[int, list[int]]) -> Path:
  for pid, tids in threads.items():
    for tid in tids:
      (root / str(pid) / 'task' / str(tid)).mkdir(parents=True)
  return root


def test_every_thread_moves_to_the_music_core_at_music_nice(tmp_path, monkeypatch):
  # pulseaudio (20) drops the nice it inherits; soloist's threads (30, 31) were reset by power saving.
  scheduler = FakeScheduler({20: {0, 1, 2, 3}, 30: set(range(8)), 31: set(range(8)), 10: {7}},
                            {20: 0, 30: 10, 31: 10, 10: 10})
  scheduler.install(monkeypatch)
  proc = tasks(tmp_path, {10: [10], 20: [20], 30: [30, 31]})
  supervisor.place_music([10, 20, 30], proc=proc, core_online=lambda core: core == 7)
  assert all(cores == {supervisor.MUSIC_CORE} for cores in scheduler.affinity.values())
  assert sorted(scheduler.pinned) == [20, 30, 31]  # the already placed thread is left alone
  assert scheduler.nice == {20: supervisor.MUSIC_NICE, 30: 10, 31: 10, 10: 10}
  assert scheduler.reniced == [20]


def test_offline_core_and_exited_processes_are_left_alone(tmp_path, monkeypatch):
  scheduler = FakeScheduler({20: {0, 1, 2, 3}}, {20: 0})
  scheduler.install(monkeypatch)
  proc = tasks(tmp_path, {20: [20], 40: [40]})
  supervisor.place_music([20, 40, 50], proc=proc, core_online=lambda core: False)
  assert scheduler.pinned == [] and scheduler.reniced == []
  # Parked core back online: a thread that exited after listing (40) and a missing process (50) are skipped.
  supervisor.place_music([20, 40, 50], proc=proc, core_online=lambda core: True)
  assert scheduler.affinity[20] == {supervisor.MUSIC_CORE}
  assert scheduler.nice[20] == supervisor.MUSIC_NICE


@pytest.mark.parametrize('platform', ['darwin', 'win32'])
def test_other_platforms_are_untouched(tmp_path, monkeypatch, platform):
  scheduler = FakeScheduler({20: {0}}, {20: 0})
  scheduler.install(monkeypatch)
  monkeypatch.setattr(supervisor.sys, 'platform', platform)
  supervisor.place_music([20], proc=tasks(tmp_path, {20: [20]}), core_online=lambda core: True)
  assert scheduler.pinned == []


def test_core_online_reads_sysfs(tmp_path):
  (tmp_path / 'cpu7').mkdir()
  (tmp_path / 'cpu7' / 'online').write_text('1\n')
  (tmp_path / 'cpu6').mkdir()
  (tmp_path / 'cpu6' / 'online').write_text('0\n')
  assert supervisor._core_online(7, tmp_path)
  assert not supervisor._core_online(6, tmp_path)
  assert not supervisor._core_online(5, tmp_path)
