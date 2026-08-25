from pathlib import Path
import runpy

import pytest

from tools.agnos.patch_system_reset_image import (
  AMDGPU_FIRMWARE_SHA256,
  COMMA_SH_DISPLAY_WAIT_PATCH_MARKER,
  comma_sh_has_expected_display_wait,
  find_default_reference_manifest,
  format_debugfs_mode,
  patch_comma_sh_display_wait,
  patch_setup_branding_script,
  sha256_zstd_payload,
)


ORIGINAL_DISPLAY_WAIT = b'''#!/usr/bin/env bash
echo "waiting for magic"
for i in {1..200}; do
  if systemctl is-active --quiet magic && [ -S /tmp/drmfd.sock ]; then
    break
  fi
  sleep 0.1
done

if systemctl is-active --quiet magic && [ -S /tmp/drmfd.sock ]; then
  echo "magic ready after ${SECONDS}s"
else
  echo "timed out waiting for magic, ${SECONDS}s"
fi

exec /data/continue.sh
'''


def test_patch_comma_sh_display_wait_uses_available_display_service():
  patched = patch_comma_sh_display_wait(ORIGINAL_DISPLAY_WAIT)

  assert COMMA_SH_DISPLAY_WAIT_PATCH_MARKER.encode() in patched
  assert b"systemctl cat magic.service" in patched
  assert b"systemctl is-active --quiet magic" in patched
  assert b"systemctl is-active --quiet weston-ready" in patched
  assert b"[ -S /var/tmp/weston/wayland-0 ]" in patched
  assert comma_sh_has_expected_display_wait(patched)
  assert patch_comma_sh_display_wait(patched) == patched


def test_patch_comma_sh_display_wait_rejects_unknown_layout():
  with pytest.raises(RuntimeError, match="display readiness wait"):
    patch_comma_sh_display_wait(b"#!/usr/bin/env bash\nexec /data/continue.sh\n")


@pytest.mark.parametrize("slider_text", ["slide to use", "slide to install"])
def test_patch_mici_setup_branding_handles_old_and_new_labels(slider_text):
  original = f'''OPENPILOT_URL = "https://openpilot.comma.ai"
self._openpilot_slider = LargerSlider("{slider_text}\\nopenpilot", callback)
self._continue_button = BigPillButton("install openpilot", green=True)
self._continue_button.set_text("install openpilot" if not custom_software else "choose software")
'''.encode()

  patched = patch_setup_branding_script(original, "openpilot/system/ui/mici_setup.py")

  assert b"installer.comma.ai/firestar5683/StarPilot" in patched
  assert f"{slider_text}\\nstarpilot".encode() in patched
  assert b"install StarPilot" in patched
  assert b"install openpilot" not in patched


@pytest.mark.parametrize(("mode", "expected"), [
  ("100775", "0100775"),
  ("100644", "0100644"),
  ("040755", "040755"),
  ("120777", "0120777"),
])
def test_format_debugfs_mode(mode, expected):
  assert format_debugfs_mode(mode) == expected


def test_external_gpu_firmware_matches_tinygrad_requirements():
  firmware_metadata = Path(__file__).resolve().parents[2] / "tinygrad/runtime/autogen/am/fw.py"
  hashes = runpy.run_path(firmware_metadata)["hashes"]
  expected = {filename.removesuffix(".zst"): digest for filename, digest in AMDGPU_FIRMWARE_SHA256.items()}
  assert all(hashes[filename] == digest for filename, digest in expected.items())


def test_zstd_payload_hash(tmp_path):
  import hashlib
  import zstandard

  payload = b"external GPU firmware payload"
  compressed = tmp_path / "firmware.bin.zst"
  compressed.write_bytes(zstandard.ZstdCompressor().compress(payload))

  assert sha256_zstd_payload(compressed) == hashlib.sha256(payload).hexdigest()


def test_default_reference_manifest_uses_sibling_openpilot(tmp_path):
  primary = tmp_path / "starpilot/system/hardware/tici/agnos.json"
  reference = tmp_path / "openpilot/openpilot/system/hardware/tici/agnos.json"
  primary.parent.mkdir(parents=True)
  reference.parent.mkdir(parents=True)
  primary.write_text("[]")
  reference.write_text("[]")

  assert find_default_reference_manifest(primary) == reference.resolve()
