"""Continental ARS510 ACC target plus the radar's target summaries: up to three points per radar cycle.

The radar's ACC target (0x235 / 0x237) is published as in `acc`. The target summaries add up to two more moving cars from
the same tracker: range and lateral in 0x192 / 0x194, a pair code in 0x191 / 0x193 (trackId 64 + code). A summary within
1 m / 0.5 m of the ACC point is that car and is skipped. vRel is the least-squares slope of the code's last 8 ranges
over CAN time (the 8 must span less than 0.6 s). Summaries beyond 40 m are left out: radard cannot tell a neighbouring
lane from the camera's farther lead there (at 47-58 m it took such a car as the lead before the radar's ACC picked the real one).

Adapted from ds-sebastian/ars510-radar at de3da93527f3e5dba08c2ea872b1bd9ac4aaa41f (openpilot/standalone/ars510_acc_summaries.py;
evidence and replay numbers in its docs/11, "acc_summaries").
Copyright (c) 2026 ARS510 radar contributors. MIT license; see THIRD_PARTY_NOTICES.md.
"""
from collections import deque
from functools import reduce
from math import nan

from opendbc.car import structs
from opendbc.car.interfaces import RadarInterfaceBase

# JUMP_M: a range step this large between cycles is a glitch, a new car, or two cars sharing a pair code (codes are per slot)
STALE_S, FAR_M, SLOPE_N, SLOPE_SPAN_S, JUMP_M, SUMMARY_ID = 0.5, 40.0, 8, 0.6, 5.0, 64  # summary trackIds: 64 + pair code
# 0x237's lateral field is the low 12 bits of a 13-bit value: beyond 20.95 m left it wraps by 40.96 m. Its check byte (CRC-8
# over the signals, linear: one column per payload bit from byte 1 bit 7, constant 0xFE; docs/05) is then off by 0x14.
LAT_CHECK = bytes.fromhex("0f89ca6599c261be5fa1de6fb9d269ba5d0a058c46239fc1ee77b5d46a35944a259c4e279dc06030180c06038f272c2eefef9898771d3a74")


def bits(b, start, length):
  return (int.from_bytes(b, "big") >> start) & ((1 << length) - 1)


def slope(hist):
  tm, dm = sum(t for t, _ in hist) / len(hist), sum(d for _, d in hist) / len(hist)
  return sum((t - tm) * (d - dm) for t, d in hist) / sum((t - tm) ** 2 for t, _ in hist)


def point(track_id, d, y, v):
  return structs.RadarData.RadarPoint(trackId=track_id, dRel=d, yRel=y, vRel=v, aRel=nan, yvRel=nan, measured=True)


class RadarInterface(RadarInterfaceBase):
  def __init__(self, CP):
    super().__init__(CP)
    self.speed = self.pos = self.last_t = None
    self.ident, self.summaries, self.ranges = {}, {}, {}

  def update(self, can_packets):
    self.frame += 1
    t = None
    for nanos, frames in can_packets:
      t = nanos * 1e-9
      for address, dat, src in frames:
        if src != 1:
          continue
        if address == 0x235 and len(dat) == 8:  # target id, closing speed; status nibble 5 = target present
          self.last_t, self.speed = t, (bits(dat, 0, 6), (bits(dat, 29, 11) - 1024) * 0.125) if dat[1] & 0x0F == 5 else None
        elif address == 0x237 and len(dat) == 8:  # distance, lateral (left positive, unwrapped); bit 10 = target present
          wrapped = reduce(lambda crc, i: crc ^ LAT_CHECK[i] * bits(dat, 55 - i, 1), range(len(LAT_CHECK)), 0xFE ^ dat[0]) == 0x14
          lat = (bits(dat, 27, 12) - 2000) * 0.01 + 40.96 * wrapped
          self.last_t, self.pos = t, (bits(dat, 39, 13) * 0.025, lat) if bits(dat, 10, 1) else None
        elif address in (0x191, 0x193) and len(dat) == 8:  # byte 0 >> 1: score (127 = no car), byte 3 >> 2: pair code
          self.ident[address] = dat
        elif address in (0x192, 0x194) and len(dat) >= 4 and address - 1 in self.ident:  # range, lateral (left positive)
          ident, self.summaries[address] = self.ident[address - 1], None
          # top 3 bits of each word are 0 unless corrupt (e.g. FF FF FF FF)
          if dat[0:4] != b"\x00\xff\x00\xff" and not (dat[0] | dat[2]) & 0xE0 and ident[0] >> 1 != 127:
            code, d = ident[3] >> 2, (bits(dat[0:2], 0, 13) - 160) / 16
            hist = self.ranges.setdefault(code, deque(maxlen=SLOPE_N))
            if hist and abs(d - hist[-1][1]) > JUMP_M:  # no car moves 5 m in one 60 ms cycle: restart rather than slope through it
              hist.clear()
            hist.append((t, d))
            self.summaries[address] = (code, d, (bits(dat[2:4], 0, 13) - 2048) * 0.015, t)
    if t is None or self.frame % 5 != 0:  # card calls update at 100 Hz: report at 20 Hz
      return None
    ret = structs.RadarData()
    if self.last_t is None or t - self.last_t > STALE_S:
      ret.errors.radarUnavailableTemporary = self.last_t is not None
      return ret
    points = [point(self.speed[0], *self.pos, self.speed[1])] if self.speed is not None and self.pos is not None else []
    for code, d, y, ts in filter(None, self.summaries.values()):
      hist = self.ranges[code]
      is_acc = self.pos is not None and abs(d - self.pos[0]) < 1.0 and abs(y - self.pos[1]) < 0.5
      if t - ts < STALE_S and d <= FAR_M and not is_acc and len(hist) == SLOPE_N and hist[-1][0] - hist[0][0] < SLOPE_SPAN_S:
        points.append(point(SUMMARY_ID + code, d, y, slope(hist)))
    ret.points = points
    return ret
