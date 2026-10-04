import pytest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR, CarControllerParams


MUTATORS = ((CAR.HONDA_CIVIC_BOSCH, 750), (CAR.HONDA_ODYSSEY_5G_MMR, 2000), (CAR.ACURA_RDX_3G_MMR, 2000))


def interface(identity):
  cp = CarInterface.get_params(identity, gen_empty_fingerprint(), [], True, False, False)
  ci = CarInterface(cp)
  ci.update([])
  return ci


def output(ci):
  command = structs.CarControl(enabled=True, longActive=True, latActive=False)
  command.actuators.accel = 1.0
  command.actuators.longControlState = "pid"
  return [ci.apply(command.as_reader(), 1_000_000_000 + tick * 10_000_000)[1] for tick in range(20)]


@pytest.mark.parametrize("identity,maximum", MUTATORS)
@pytest.mark.parametrize("sibling", (CAR.HONDA_ACCORD, CAR.HONDA_CRV_5G))
def test_real_factory_controller_output_is_independent_of_other_vehicle_construction(identity, maximum, sibling, monkeypatch):
  monkeypatch.setattr(CarControllerParams, "BOSCH_GAS_LOOKUP_V", [0, 1600])
  baseline = interface(sibling)
  expected = output(baseline)
  changed = interface(identity)
  assert changed.CC.params.BOSCH_GAS_LOOKUP_V == [0, maximum]
  later = interface(sibling)
  assert later.CC.params.BOSCH_GAS_LOOKUP_V == [0, 1600]
  assert output(later) == expected
  assert CarControllerParams.BOSCH_GAS_LOOKUP_V == [0, 1600]
  changed.CC.params.BOSCH_GAS_LOOKUP_V[1] = 1
  changed.CC.params.BOSCH_GAS_LOOKUP_BP[0] = 1.0
  assert baseline.CC.params.BOSCH_GAS_LOOKUP_V == later.CC.params.BOSCH_GAS_LOOKUP_V == [0, 1600]
  assert baseline.CC.params.BOSCH_GAS_LOOKUP_BP == later.CC.params.BOSCH_GAS_LOOKUP_BP == [-0.2, 2.0]
