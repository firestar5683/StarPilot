"""Fresh proposal acceptance; selfdrived alone chooses its effective mode."""

from dataclasses import dataclass

from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.conditional_mode.projection import CLOCK_PAIR_MAX_SKEW_NS
from openpilot.starpilot.conditional_mode.status import LIFETIME_NS, MODEL_MAX_AGE_NS, ModeObservation, observation


@dataclass(frozen=True)
class ConsumerResult:
  experimental: bool
  accepted: bool
  status: str


class ModeConsumer:
  def __init__(self):
    self.barrier_ns = 0
    self.offset_ns: int | None = None
    self.last_now_ns = 0
    self.drive_id = 0
    self.last: ModeObservation | None = None

  def invalidate(self, now_ns: int) -> None:
    self.barrier_ns = max(self.barrier_ns, now_ns)
    self.last = None

  def sample(
    self,
    state,
    *,
    now_ns: int,
    now_boot_ns: int,
    sample_skew_ns: int,
    message_ns: int,
    receipt_ns: int,
    drive_id: int,
    model_ns: int,
    car_state_ns: int,
    authority: bool,
    stock_experimental: bool,
    choice: ModeChoice,
    settings_fingerprint: str | None,
  ) -> ConsumerResult:
    """A repeated message may be used until its original expiry, never renewed.

    The caller checks live native longitudinal authority and independently
    affirms the saved settings. The publisher's authority cannot substitute for
    either. A restart, clock discontinuity or drive change requires new sources.
    """
    fallback = ConsumerResult(stock_experimental if type(stock_experimental) is bool else False, False, 'unavailable')
    if (
      any(type(value) is not int for value in (now_ns, now_boot_ns, sample_skew_ns, message_ns, receipt_ns, drive_id, model_ns, car_state_ns))
      or now_ns <= 0
      or now_boot_ns < now_ns
      or not 0 <= sample_skew_ns <= CLOCK_PAIR_MAX_SKEW_NS
    ):
      self.invalidate(self.last_now_ns)
      return fallback
    offset = now_boot_ns - now_ns
    discontinuity = self.offset_ns is None or abs(offset - self.offset_ns) > CLOCK_PAIR_MAX_SKEW_NS or now_ns < self.last_now_ns or drive_id != self.drive_id
    self.last_now_ns = now_ns
    self.offset_ns = offset
    self.drive_id = drive_id
    if discontinuity:
      self.invalidate(now_ns)
      return fallback
    if (
      authority is not True
      or type(stock_experimental) is not bool
      or choice not in (ModeChoice.CEM, ModeChoice.CCM, ModeChoice.STOCK)
      or settings_fingerprint is None
      or not 0 < drive_id <= now_ns
      or not self.barrier_ns < model_ns <= now_ns
      or now_ns - model_ns > MODEL_MAX_AGE_NS
      or not self.barrier_ns < car_state_ns <= now_ns
      or now_ns - car_state_ns > LIFETIME_NS
    ):
      self.invalidate(now_ns)
      return fallback
    value = observation(state, now_ns)
    if (
      value is None
      or value.drive_id != drive_id
      or value.choice is not choice
      or value.fingerprint != settings_fingerprint
      or value.override is None
      or choice is ModeChoice.STOCK and (value.reason != 'cem_stop' or value.status_code != 8 or value.override is not True)
      or not self.barrier_ns < message_ns <= value.observed_ns <= now_ns
      or value.observed_ns - message_ns > LIFETIME_NS
      or not message_ns <= receipt_ns <= now_ns
      or now_ns - receipt_ns > LIFETIME_NS
      or not self.barrier_ns < value.model_ns <= model_ns
      or now_ns - value.model_ns > MODEL_MAX_AGE_NS
      or not self.barrier_ns < value.car_state_ns <= car_state_ns
      or now_ns - value.car_state_ns > LIFETIME_NS
    ):
      # Preserve the last sequence to reject old or altered samples after gaps.
      return fallback
    previous = self.last
    if previous is not None:
      if value.session != previous.session:
        self.invalidate(now_ns)
        return fallback
      if value.sequence < previous.sequence or value.sequence == previous.sequence and value != previous:
        return fallback
      if value.sequence > previous.sequence and (value.observed_ns <= previous.observed_ns or value.model_ns <= previous.model_ns):
        return fallback
    self.last = value
    return ConsumerResult(value.override, True, value.status)
