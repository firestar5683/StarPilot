"""Adapter to the proposed BluePilot library; angle only, exact source pinned."""
from opendbc.bluepilot_lateral.can.ford import lateral, lka
from opendbc.bluepilot_lateral.core.angle import Command
from opendbc.bluepilot_lateral.hosts.starpilot import Host, qualified


class BluePilotLateral:
  def __init__(self, CP, *, host=None):
    if not qualified(CP):
      raise ValueError("Angle mode is not configured")
    self.host = host or Host(CP)
    self.canfd = bool(CP.flags & 1)
    self.pending = Command()
    self.announced = Command()
    self.announced_ns = 0
    self.lka_counter = 0
    self.apply_curvature_last = 0.0

  def step_lateral(self, CC, CS, packer, CAN, frame, now_ns):
    self.pending = self.host.update(CC, CS)
    command = self.announced
    # A pending permission withdrawal is immediate; an increase waits until
    # the 33Hz side channel has announced the matching final actuator.
    if not self.pending.active or not 0 < self.announced_ns <= now_ns <= self.announced_ns + 60_000_000:
      command = Command()
      self.announced = command
    return [lateral(packer, CAN.main, command, canfd=self.canfd, counter=frame // 5)]

  def step_lka(self, packer, CAN, now_ns):
    self.announced = self.pending
    self.announced_ns = now_ns
    message = lka(packer, CAN.main, self.announced.shadow_curvature, self.lka_counter)
    self.lka_counter = (self.lka_counter + 1) % 8
    return [message]
