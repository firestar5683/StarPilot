"""GM-owned AOL capabilities; exact CP admission lives with the vehicle."""

from opendbc.car.structs import CarParams
from opendbc.car.gm.aol import GM_AOL_ALTERNATIVE_EXPERIENCE, GM_AOL_WORDS, qualified_gm
from openpilot.starpilot.aol.policy import AolVehiclePolicy
from openpilot.starpilot.aol.intent import AolCardIntent


def policy_for(cp) -> AolVehiclePolicy:
  qualified = qualified_gm(cp)
  return AolVehiclePolicy(intent_supported=qualified, settings_supported=qualified,
                         runtime_supported=qualified, normal_runtime_supported=qualified,
                         alternative_experience_addition=GM_AOL_ALTERNATIVE_EXPERIENCE if qualified else 0)


def native_profile_supported(model: int, param: int) -> bool:
  return model == int(CarParams.SafetyModel.gm) and param in GM_AOL_WORDS


def native_accepts_cp(cp, model: int, param: int) -> bool:
  return (qualified_gm(cp) and int(cp.alternativeExperience) == GM_AOL_ALTERNATIVE_EXPERIENCE and
          native_profile_supported(model, param))


class GmAolCardIntent(AolCardIntent):
  """Main-following intent with explicit main-cycle recovery after fatal faults."""

  def __init__(self, settings):
    super().__init__(settings)
    self.requires_fault_observation = True
    self._main_cycle_required = False

  def update(self, CS, *, consumed_buttons=frozenset(), fault_active=None,
             now_ns=0, native_rejection_ns=0, standard_enabled=False):
    fault = bool(fault_active or CS.steerFaultPermanent)
    if fault:
      self._main_cycle_required = True
    elif CS.canValid and not CS.canTimeout and not CS.cruiseState.available:
      self._main_cycle_required = False
    super().update(CS, consumed_buttons=consumed_buttons, fault_active=fault_active,
                   now_ns=now_ns, native_rejection_ns=native_rejection_ns,
                   standard_enabled=standard_enabled)
    if self._main_cycle_required:
      self.allowed_latch = False


def create_intent(cp, settings):
  return GmAolCardIntent(settings) if qualified_gm(cp) else None
