from dataclasses import dataclass, field
from enum import IntFlag
from opendbc.car import Bus, CarSpecs, DbcDict, PlatformConfig, Platforms
from opendbc.car.structs import CarParams
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.docs_definitions import CarDocs, CarHarness, CarParts
from opendbc.car.fw_query_definitions import FwQueryConfig
from opendbc.car.lateral import AngleSteeringLimits

# C1 support is adapted from the original dragonpilot V40 port:
# https://github.com/dragonpilot/dragonpilot/commit/773dce507082d931236b64dca8024dce9625446f
Ecu = CarParams.Ecu


class VolvoSafetyFlags(IntFlag):
  C1 = 2


class CarControllerParams:
  C1_N_ZERO_TORQUE = 12
  C1_ANGLE_ERROR = 20.0
  C1_ANGLE_DELTA_BP = [0.0, 8.33, 13.89, 19.44, 25.0, 30.55, 36.1]
  C1_ANGLE_DELTA_UP = [2.0, 1.2, 0.25, 0.20, 0.15, 0.10, 0.10]
  C1_ANGLE_DELTA_DOWN = [2.0, 1.2, 0.25, 0.20, 0.15, 0.10, 0.10]
  C1_ANGLE_LIMITS = AngleSteeringLimits(359.9, (C1_ANGLE_DELTA_BP, C1_ANGLE_DELTA_UP), (C1_ANGLE_DELTA_BP, C1_ANGLE_DELTA_DOWN))


@dataclass
class VolvoCarDocs(CarDocs):
  package: str = "Pilot Assist & Adaptive Cruise Control"
  car_parts: CarParts = field(default_factory=lambda: CarParts.common([CarHarness.custom]))


@dataclass
class VolvoC1PlatformConfig(PlatformConfig):
  dbc_dict: DbcDict = field(default_factory=lambda: {Bus.pt: 'volvo_v40_2017_pt', Bus.cam: 'volvo_v40_2017_pt'})


class CAR(Platforms):
  VOLVO_V40 = VolvoC1PlatformConfig(
    [VolvoCarDocs("Volvo V40 2013-19")], CarSpecs(mass=1610, wheelbase=2.647, steerRatio=14.7, centerToFrontRatio=0.44, minSteerSpeed=1.0 * CV.KPH_TO_MS)
  )


FW_QUERY_CONFIG = FwQueryConfig(requests=[], fw_version_regex=br"(?!)")
DBC = CAR.create_dbc_map()
