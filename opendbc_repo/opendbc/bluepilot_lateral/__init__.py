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
    self.control_counter = 0
    self.control_sent_ns = 0
    self.shadow_sent_ns = 0
    self.control_echo_ns = 0
    self.shadow_echo_ns = 0
    self.control_returned_ns = 0
    self.shadow_returned_ns = 0
    self.control_echo_pending = False
    self.shadow_echo_pending = False
    self.shadow_rejection_pending = False
    self.control_return_payload = None
    self.shadow_return_payload = None
    self.pending_generation = 0
    self.announced_generation = -1
    self.sent_generation = -2
    self.steering_rejection_ns = 0
    self.apply_curvature_last = 0.0

  def observe_can(self, can_packets, main_bus):
    # Forwarded stock traffic also returns with src|0x80. Consume one matching
    # return for our actual emitted payload; unrelated stock echoes cannot pace us.
    # Preserve return ordering here;
    # start the delay when consumed, in the controller's own clock domain.
    control_address = 0x3D6 if self.canfd else 0x3D3
    for timestamp, frames in can_packets:
      if timestamp <= 0:
        continue
      for address, data, source in frames:
        if len(data) != 8:
          continue
        if source == (main_bus | 0xC0) and address in (control_address, 0x3CA):
          if timestamp > self.steering_rejection_ns:
            self.steering_rejection_ns = timestamp
            self.host.steering_rejected = True
          if address == 0x3CA and data == self.shadow_return_payload:
            self.lka_counter = (data[4] >> 2) & 7
            self.shadow_return_payload = None
            self.shadow_rejection_pending = True
          continue
        if source != (main_bus | 0x80):
          continue
        if address == control_address and data == self.control_return_payload and timestamp > self.control_returned_ns:
          self.control_return_payload = None
          self.control_returned_ns = timestamp
          self.control_echo_pending = True
        elif address == 0x3CA and data == self.shadow_return_payload and timestamp > self.shadow_returned_ns:
          self.shadow_return_payload = None
          self.shadow_returned_ns = timestamp
          self.shadow_echo_pending = True

  def step_lateral(self, CC, CS, packer, CAN, frame, now_ns):
    if now_ns <= 0:
      return []
    if self.control_echo_pending:
      self.control_echo_ns = now_ns
      self.control_echo_pending = False
    if ((self.control_sent_ns and now_ns - self.control_sent_ns < 50_000_000) or
        (self.control_echo_ns and now_ns - self.control_echo_ns < 45_000_000) or
        self.announced_generation <= self.sent_generation):
      return []
    self.pending = self.host.update(CC, CS)
    self.pending_generation += 1
    command = self.announced
    # A pending permission withdrawal is immediate; an increase waits until
    # the 33Hz side channel has announced the matching final actuator.
    fresh = 0 < self.announced_ns <= now_ns <= self.announced_ns + 60_000_000
    if not self.pending.active or not fresh:
      command = Command()
      self.announced = command
      if not fresh:
        # Native records the neutral actuator as zero. Do not resume an old
        # nonzero path after a new announcement; restart through the normal limits.
        self.host.controller.reset_actuator()
        self.pending = Command()
    self.control_sent_ns = now_ns
    self.sent_generation = self.announced_generation
    message = lateral(packer, CAN.main, command, canfd=self.canfd, counter=self.control_counter)
    self.control_return_payload = message[1]
    self.control_counter = (self.control_counter + 1) % 16
    return [message]

  def step_lka(self, packer, CAN, now_ns):
    if now_ns <= 0:
      return []
    if self.shadow_echo_pending or self.shadow_rejection_pending:
      self.shadow_echo_ns = now_ns
      self.shadow_echo_pending = False
      self.shadow_rejection_pending = False
    if (self.shadow_return_payload is not None or
        (self.shadow_sent_ns and now_ns - self.shadow_sent_ns < 30_000_000) or
        (self.shadow_echo_ns and now_ns - self.shadow_echo_ns < 25_000_000)):
      return []
    self.announced = self.pending
    self.announced_generation = self.pending_generation
    self.announced_ns = now_ns
    self.shadow_sent_ns = now_ns
    message = lka(packer, CAN.main, self.announced.shadow_curvature, self.lka_counter)
    self.shadow_return_payload = message[1]
    self.lka_counter = (self.lka_counter + 1) % 8
    return [message]
