import unittest

from opendbc.car import structs
from opendbc.car.ford.values import CAR
from opendbc.car.fw_versions import match_fw_to_car

Ecu = structs.CarParams.Ecu

SOURCE_BASELINES = {
  CAR.FORD_BRONCO_SPORT_MK1: {
    (Ecu.eps, 1840, None): b'LX6C-14D003-AH\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.abs, 1888, None): b'LX6C-2D053-KF\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdRadar, 1892, None): b'LB5T-14D049-AB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdCamera, 1798, None): b'M1PT-14F397-AC\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
  },
  CAR.FORD_ESCAPE_MK4_5: {
    (Ecu.eps, 1840, None): b'PZ11-14D003-AB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.abs, 1888, None): b'PZ1C-2D053-EJ\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdRadar, 1892, None): b'ML3T-14D049-AL\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdCamera, 1798, None): b'PJ6T-14H102-ABE\x00\x00\x00\x00\x00\x00\x00\x00\x00',
  },
  CAR.FORD_EXPEDITION_MK4: {
    (Ecu.eps, 1840, None): b'NL14-14D003-AE\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.abs, 1888, None): b'RL14-2D053-AA\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdRadar, 1892, None): b'ML3T-14D049-AL\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdCamera, 1798, None): b'ML3T-14H102-ABT\x00\x00\x00\x00\x00\x00\x00\x00\x00',
  },
  CAR.FORD_EXPLORER_MK6: {
    (Ecu.eps, 1840, None): b'R1MC-14D003-AE\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.abs, 1888, None): b'L1MC-2D053-AJ\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdRadar, 1892, None): b'LB5T-14D049-AB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdCamera, 1798, None): b'LB5T-14F397-AD\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
  },
  CAR.FORD_FOCUS_MK4: {
    (Ecu.eps, 1840, None): b'JX6C-14D003-AH\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.abs, 1888, None): b'JX61-2D053-CJ\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdRadar, 1892, None): b'JX7T-14D049-AC\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdCamera, 1798, None): b'JX7T-14F397-AH\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
  },
  CAR.FORD_F_150_LIGHTNING_MK1: {
    (Ecu.abs, 1888, None): b'NL38-2D053-AF\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdCamera, 1798, None): b'ML3T-14H102-ABT\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdRadar, 1892, None): b'ML3T-14D049-AH\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.eps, 1840, None): b'NL38-14D003-AA\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
  },
  CAR.FORD_F_150_MK14: {
    (Ecu.eps, 1840, None): b'MB3C-14D003-AA\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.abs, 1888, None): b'ML34-2D053-AJ\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdRadar, 1892, None): b'ML3T-14D049-AH\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdCamera, 1798, None): b'ML3T-14H102-ABR\x00\x00\x00\x00\x00\x00\x00\x00\x00',
  },
  CAR.FORD_MUSTANG_MACH_E_MK1: {
    (Ecu.eps, 1840, None): b'LJ9C-14D003-AM\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.abs, 1888, None): b'LK9C-2D053-CK\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdRadar, 1892, None): b'ML3T-14D049-AH\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdCamera, 1798, None): b'ML3T-14H102-ABS\x00\x00\x00\x00\x00\x00\x00\x00\x00',
  },
  CAR.FORD_RANGER_MK2: {
    (Ecu.eps, 1840, None): b'JR3C-14D003-AA\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.abs, 1888, None): b'MB3C-2D053-AE\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdRadar, 1892, None): b'JX7T-14D049-AD\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdCamera, 1798, None): b'PJ6T-14H102-ABJ\x00\x00\x00\x00\x00\x00\x00\x00\x00',
  },
  CAR.FORD_TRANSIT_MK5: {
    (Ecu.eps, 1840, None): b'KK21-14D003-AM\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.abs, 1888, None): b'NK41-2D053-DF\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdRadar, 1892, None): b'PC4T-14D049-AA\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    (Ecu.fwdCamera, 1798, None): b'NK3T-14F397-AB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
  },
}

ADDED_VERSIONS = (
  (CAR.FORD_BRONCO_SPORT_MK1, (Ecu.abs, 1888, None), b'LX6C-2D053-KF\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_BRONCO_SPORT_MK1, (Ecu.abs, 1888, None), b'LX6C-2D053-KG\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_ESCAPE_MK4_5, (Ecu.eps, 1840, None), b'PZ11-14D003-AB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_ESCAPE_MK4_5, (Ecu.eps, 1840, None), b'PZ11-14D003-FA\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_ESCAPE_MK4_5, (Ecu.fwdCamera, 1798, None), b'PJ6T-14H102-ABE\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_ESCAPE_MK4_5, (Ecu.fwdCamera, 1798, None), b'PJ6T-14H102-MDC\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_ESCAPE_MK4_5, (Ecu.fwdCamera, 1798, None), b'PJ6T-14H102-MDF\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_ESCAPE_MK4_5, (Ecu.fwdCamera, 1798, None), b'PJ6T-14H102-SCD\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_ESCAPE_MK4_5, (Ecu.fwdCamera, 1798, None), b'PJ6T-14H102-SCG\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_EXPLORER_MK6, (Ecu.eps, 1840, None), b'R1MC-14D003-AE\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_EXPLORER_MK6, (Ecu.eps, 1840, None), b'R1MC-14D003-AF\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_EXPLORER_MK6, (Ecu.eps, 1840, None), b'R1MC-14D003-AG\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_EXPLORER_MK6, (Ecu.eps, 1840, None), b'R1MC-14D003-AH\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_EXPEDITION_MK4, (Ecu.abs, 1888, None), b'PL14-2D053-AB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_F_150_MK14, (Ecu.eps, 1840, None), b'MB3C-14D003-AA\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_F_150_LIGHTNING_MK1, (Ecu.abs, 1888, None), b'NL38-2D053-AF\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_F_150_LIGHTNING_MK1, (Ecu.abs, 1888, None), b'RL38-2D053-BC\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_F_150_LIGHTNING_MK1, (Ecu.abs, 1888, None), b'TL38-2D053-AD\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_F_150_LIGHTNING_MK1, (Ecu.fwdRadar, 1892, None), b'ML3T-14D049-AH\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_F_150_LIGHTNING_MK1, (Ecu.fwdRadar, 1892, None), b'RB5T-14D049-AB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_F_150_LIGHTNING_MK1, (Ecu.eps, 1840, None), b'NL38-14D003-AA\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_F_150_LIGHTNING_MK1, (Ecu.eps, 1840, None), b'NL38-14D003-AC\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_MUSTANG_MACH_E_MK1, (Ecu.fwdRadar, 1892, None), b'ML3T-14D049-AH\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_MUSTANG_MACH_E_MK1, (Ecu.fwdRadar, 1892, None), b'ML3T-14D049-AK\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_FOCUS_MK4, (Ecu.eps, 1840, None), b'JX6C-14D003-AL\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_FOCUS_MK4, (Ecu.eps, 1840, None), b'JX6C-14D003-BB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_FOCUS_MK4, (Ecu.abs, 1888, None), b'NX61-2D053-MD\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_RANGER_MK2, (Ecu.eps, 1840, None), b'JR3C-14D003-AA\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_RANGER_MK2, (Ecu.eps, 1840, None), b'NL14-14D003-AC\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_RANGER_MK2, (Ecu.abs, 1888, None), b'MB3C-2D053-AE\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_RANGER_MK2, (Ecu.abs, 1888, None), b'MB3C-2D053-ZJ\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_RANGER_MK2, (Ecu.abs, 1888, None), b'PB3C-2D053-ZB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_RANGER_MK2, (Ecu.abs, 1888, None), b'PB3C-2D053-ZC\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_RANGER_MK2, (Ecu.abs, 1888, None), b'PB9C-2D053-ZG\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_RANGER_MK2, (Ecu.fwdRadar, 1892, None), b'JX7T-14D049-AD\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
  (CAR.FORD_TRANSIT_MK5, (Ecu.fwdCamera, 1798, None), b'NK3T-14F397-AB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
)


class TestAddedFordFirmwareIdentity(unittest.TestCase):
  def test_original_literal_versions_match_joint_production_inventory(self):
    for candidate, ecu_key, version in ADDED_VERSIONS:
      cohort = dict(SOURCE_BASELINES[candidate])
      cohort[ecu_key] = version
      firmware = [
        structs.CarParams.CarFw(ecu=ecu, address=address, subAddress=0 if sub is None else sub, fwVersion=value, brand="ford")
        for (ecu, address, sub), value in cohort.items()
      ]
      for allow_exact in (True, False):
        with self.subTest(candidate=candidate, ecu=ecu_key, version=version, allow_exact=allow_exact):
          self.assertEqual(match_fw_to_car(firmware, "", allow_exact=allow_exact, log=False)[1], {candidate})

  def test_missing_required_ecu_never_falls_back_to_vin(self):
    for candidate, cohort in SOURCE_BASELINES.items():
      for omitted in cohort:
        firmware = [
          structs.CarParams.CarFw(ecu=ecu, address=address, subAddress=0 if sub is None else sub, fwVersion=value, brand="ford")
          for (ecu, address, sub), value in cohort.items()
          if (ecu, address, sub) != omitted
        ]
        for allow_exact in (True, False):
          with self.subTest(candidate=candidate, omitted=omitted, allow_exact=allow_exact):
            self.assertEqual(match_fw_to_car(firmware, "WF0XXXXXX00000000", allow_exact=allow_exact, log=False)[1], set())

  def test_unknown_required_firmware_pair_is_rejected(self):
    for candidate, cohort in SOURCE_BASELINES.items():
      for changed in cohort:
        firmware = [
          structs.CarParams.CarFw(
            ecu=ecu, address=address, subAddress=0 if sub is None else sub, fwVersion=b"UNRECOGNIZED" if (ecu, address, sub) == changed else value, brand="ford"
          )
          for (ecu, address, sub), value in cohort.items()
        ]
        for allow_exact in (True, False):
          with self.subTest(candidate=candidate, changed=changed, allow_exact=allow_exact):
            self.assertEqual(match_fw_to_car(firmware, "", allow_exact=allow_exact, log=False)[1], set())
