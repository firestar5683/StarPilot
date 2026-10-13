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
    self.rejection: str | None = None

  def invalidate(self, now_ns: int) -> None:
    self.barrier_ns = max(self.barrier_ns, now_ns)
    self.last = None

  def _reject(self, label: str, fallback: ConsumerResult, invalidate_ns: int | None = None) -> ConsumerResult:
    self.rejection = label
    if invalidate_ns is not None:
      self.invalidate(invalidate_ns)
    return fallback

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
    self.rejection = None
    if (
      any(type(value) is not int for value in (now_ns, now_boot_ns, sample_skew_ns, message_ns, receipt_ns, drive_id, model_ns, car_state_ns))
      or now_ns <= 0
      or now_boot_ns < now_ns
      or not 0 <= sample_skew_ns <= CLOCK_PAIR_MAX_SKEW_NS
    ):
      return self._reject('clock_inputs', fallback, self.last_now_ns)
    offset = now_boot_ns - now_ns
    discontinuity = self.offset_ns is None or abs(offset - self.offset_ns) > CLOCK_PAIR_MAX_SKEW_NS or now_ns < self.last_now_ns or drive_id != self.drive_id
    self.last_now_ns = now_ns
    self.offset_ns = offset
    self.drive_id = drive_id
    if discontinuity:
      return self._reject('discontinuity', fallback, now_ns)
    if authority is not True:
      return self._reject('authority', fallback, now_ns)
    if (
      type(stock_experimental) is not bool
      or choice not in (ModeChoice.CEM, ModeChoice.CCM, ModeChoice.STOCK)
      or settings_fingerprint is None
      or not 0 < drive_id <= now_ns
    ):
      return self._reject('settings', fallback, now_ns)
    if not self.barrier_ns < model_ns:
      return self._reject('model_barrier', fallback, now_ns)
    if model_ns > now_ns or now_ns - model_ns > MODEL_MAX_AGE_NS:
      return self._reject('model_age', fallback, now_ns)
    if not self.barrier_ns < car_state_ns:
      return self._reject('car_state_barrier', fallback, now_ns)
    if car_state_ns > now_ns or now_ns - car_state_ns > LIFETIME_NS:
      return self._reject('car_state_age', fallback, now_ns)
    value = observation(state, now_ns)
    # Rejections below preserve the last sequence to reject old or altered samples after gaps.
    if value is None:
      return self._reject('proposal_invalid', fallback)
    if (
      value.drive_id != drive_id
      or value.choice is not choice
      or value.fingerprint != settings_fingerprint
      or value.override is None
      or choice is ModeChoice.STOCK and (value.reason != 'cem_stop' or value.status_code != 8 or value.override is not True)
    ):
      return self._reject('proposal_mismatch', fallback)
    if not (self.barrier_ns < message_ns and self.barrier_ns < value.model_ns and self.barrier_ns < value.car_state_ns):
      return self._reject('proposal_barrier', fallback)
    if (
      not message_ns <= value.observed_ns <= now_ns
      or value.observed_ns - message_ns > LIFETIME_NS
      or not message_ns <= receipt_ns <= now_ns
      or now_ns - receipt_ns > LIFETIME_NS
    ):
      return self._reject('proposal_receipt', fallback)
    if value.model_ns > model_ns or now_ns - value.model_ns > MODEL_MAX_AGE_NS:
      return self._reject('proposal_model_age', fallback)
    if value.car_state_ns > car_state_ns or now_ns - value.car_state_ns > LIFETIME_NS:
      return self._reject('proposal_car_state_age', fallback)
    previous = self.last
    if previous is not None:
      if value.session != previous.session:
        return self._reject('session', fallback, now_ns)
      if value.sequence < previous.sequence or value.sequence == previous.sequence and value != previous:
        return self._reject('sequence', fallback)
      if value.sequence > previous.sequence and (value.observed_ns <= previous.observed_ns or value.model_ns <= previous.model_ns):
        return self._reject('sequence_stamps', fallback)
    self.last = value
    return ConsumerResult(value.override, True, value.status)
