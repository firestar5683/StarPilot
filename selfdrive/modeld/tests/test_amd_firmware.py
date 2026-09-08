#!/usr/bin/env python3
import hashlib
from pathlib import Path

import pytest
import zstandard

from tinygrad.runtime.autogen.am import fw


CHESTNUT_FIRMWARE = (
  "gc_12_0_0_imu.bin",
  "gc_12_0_0_me.bin",
  "gc_12_0_0_mec.bin",
  "gc_12_0_0_pfp.bin",
  "gc_12_0_0_rlc.bin",
  "psp_14_0_2_sos.bin",
  "sdma_7_0_0.bin",
  "smu_14_0_2.bin",
)


@pytest.mark.parametrize("name", CHESTNUT_FIRMWARE)
def test_bundled_chestnut_firmware(name):
  path = Path(__file__).parents[1] / "firmware" / "amdgpu" / f"{name}.zst"
  blob = zstandard.ZstdDecompressor().stream_reader(path.read_bytes()).read()
  assert hashlib.sha256(blob).hexdigest() == fw.hashes[name]
