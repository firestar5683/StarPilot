"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

jetlinkd, the resident gadget owner, as an openpilot device runs it.

manager runs the fork's adapter module under the name jetlinkd, and its main()
builds an OwnerConfig and calls main() here. The owner itself is
jetlink.comma.owner; this hands it the settings, read off the params files the
config names, the chestnut's USB ids, and the provisioning run to start when
there is work.

The owner stays resident for the whole drive at about 10 MB, so this module
and everything it imports is the standard library and jetlink's light half;
tests/openpilot/test_imports.py holds the line.

manager starts it again if it dies (the fork's process_config), and every
start adopts what the last owner left. A crash loop would re-enumerate the
Jetson at every start, so the owner's own backoff holds a start back once
owners keep dying (jetlink.comma.owner.note_start).
"""
from __future__ import annotations

import signal
import sys

from jetlink.comma import gadget
from jetlink.comma import owner as comma_owner
from jetlink.openpilot.interface import OwnerConfig
from jetlink.openpilot.settings import FileParams, Settings

# the provisioning run's module. Named here and nowhere in the fork: the fork
# names its adapter, and moving the run is jetlink's business alone
WORKER = 'jetlink.openpilot.provision'


def worker(config: OwnerConfig) -> list[str]:
  """One provisioning run's argv, on this interpreter, over the fork's adapter."""
  return [sys.executable, '-m', WORKER, '--adapter', config.adapter]


def main(config: OwnerConfig) -> None:
  """Hold the gadget until manager stops this process (SIGINT, or SIGTERM)."""
  gadget.set_logger(comma_owner.logger(config.log_file))
  owner = comma_owner.Owner(worker(config), cwd=str(config.cwd), env=dict(config.env),
                            settings=Settings(FileParams(config.params_dir), config.keys),
                            chestnut_ids=config.chestnut_ids)
  signal.signal(signal.SIGTERM, owner.request_stop)
  signal.signal(signal.SIGINT, owner.request_stop)
  owner.run()
