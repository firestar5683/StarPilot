"""One-time Sonata Hybrid wheel assignment migration."""

import os

from opendbc.car.hyundai.values import CAR

MIGRATION_KEY = 'SonataHybridLKASButtonControlMigrated'


def migrate_lkas_default(cp, params):
  if (getattr(cp, 'brand', None) != 'hyundai' or
      getattr(cp, 'carFingerprint', None) != CAR.HYUNDAI_SONATA_HYBRID or params.get_bool(MIGRATION_KEY)):
    return False
  if params.get('LKASButtonControl') is None and not os.path.lexists(params.get_param_path('LKASButtonControl')):
    params.put('LKASButtonControl', 9, block=True)
  params.put_bool(MIGRATION_KEY, True, block=True)
  return True
