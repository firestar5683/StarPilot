"""Isolated desktop entry contract; these tests never create a graphics context."""

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from openpilot.starpilot.ui import host_launch
from openpilot.starpilot.ui.presentation import Profile


class TestHostLaunch(unittest.TestCase):
  def test_help_needs_no_native_import_or_host_environment(self):
    result = subprocess.run([sys.executable, "-m", "openpilot.starpilot.ui.host_launch", "large", "--help"],
                            capture_output=True, text=True, check=False)
    self.assertEqual(result.returncode, 0)
    self.assertIn("./c3", result.stdout)

  def test_profile_and_isolated_environment(self):
    with patch.object(host_launch, "font_directory", return_value=Path("/tmp/reviewed-fonts")):
      source = {"SP_HOST_RUNTIME": "1", "SP_HOST_PREFIX": "starpilot-dev-abc", "OPENPILOT_PREFIX": "starpilot-dev-abc",
                "PARAMS_ROOT": "/tmp/host-private-params"}
      for profile, big in ((Profile.LARGE, "1"), (Profile.COMPACT, "0")):
        env = host_launch.launch_environment(profile, source)
        self.assertEqual(env["BIG"], big)
        self.assertEqual(env["PARAMS_ROOT"], source["PARAMS_ROOT"])
        self.assertEqual(env["STARPILOT_UI_DEV"], "1")
        self.assertEqual(env["NOBOARD"], env["SIMULATION"])
        self.assertEqual(env["SIMULATION"], env["SKIP_FW_QUERY"])
      source["OPENPILOT_PREFIX"] = "replay-test123"
      self.assertEqual(host_launch.launch_environment(Profile.COMPACT, source)["BIG"], "0")

  def test_reject_nonprivate_source_and_explicit_missing_reviewed_font(self):
    source = {"SP_HOST_RUNTIME": "1", "SP_HOST_PREFIX": "starpilot-dev-abc", "OPENPILOT_PREFIX": "d",
              "PARAMS_ROOT": "/tmp/host-private-params"}
    with self.assertRaisesRegex(RuntimeError, "runner prefix"):
      host_launch.launch_environment(Profile.LARGE, source)
    source["OPENPILOT_PREFIX"] = "starpilot-dev-abc"
    self.assertEqual(Path(host_launch.launch_environment(Profile.LARGE, source)["STARPILOT_UI_FONT_DIR"]),
                     host_launch.font_directory(source))
    source["STARPILOT_UI_FONT_DIR"] = "/missing-fonts"
    with self.assertRaisesRegex(RuntimeError, "STARPILOT_UI_FONT_DIR"):
      host_launch.launch_environment(Profile.LARGE, source)

  def test_visual_preview_only_under_private_replay_prefix(self):
    source = {"SP_HOST_RUNTIME": "1", "SP_HOST_PREFIX": "starpilot-dev-abc", "OPENPILOT_PREFIX": "starpilot-dev-abc",
              "PARAMS_ROOT": "/tmp/host-private-params", "SP_ONROAD_VISUAL_PREVIEW": "cem,csc"}
    with patch.object(host_launch, "font_directory", return_value=Path("/tmp/reviewed-fonts")):
      with self.assertRaisesRegex(RuntimeError, "private replay prefix"):
        host_launch.launch_environment(Profile.LARGE, source)
      source["OPENPILOT_PREFIX"] = "replay-good"
      self.assertEqual(host_launch.launch_environment(Profile.COMPACT, source)["SP_ONROAD_VISUAL_PREVIEW"], "cem,csc")
      source["SP_ONROAD_VISUAL_PREVIEW"] = "csc,cem"
      self.assertEqual(host_launch.launch_environment(Profile.LARGE, source)["SP_ONROAD_VISUAL_PREVIEW"], "cem,csc")
      source["SP_ONROAD_VISUAL_PREVIEW"] = "cem,bogus"
      with self.assertRaisesRegex(ValueError, "Unknown"):
        host_launch.launch_environment(Profile.LARGE, source)
      source["SP_ONROAD_VISUAL_PREVIEW"] = ""
      self.assertNotIn("SP_ONROAD_VISUAL_PREVIEW", host_launch.launch_environment(Profile.LARGE, source))

  def test_private_first_launch_defaults_do_not_overwrite_saved_choices(self):
    from openpilot.common.params import Params
    with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, PARAMS_ROOT=directory,
                                                                   OPENPILOT_PREFIX="starpilot-dev-fixture"):
      host_launch.seed_developer_defaults()
      params = Params()
      self.assertIs(params.get("OpenpilotEnabledToggle"), True)
      self.assertEqual(params.get("LanguageSetting"), "en")
      self.assertIs(params.get("IsDriverViewEnabled"), False)
      params.put_bool("OpenpilotEnabledToggle", False, block=True)
      params.put("LanguageSetting", "es-ES", block=True)
      host_launch.seed_developer_defaults()
      self.assertIs(params.get("OpenpilotEnabledToggle"), False)
      self.assertEqual(params.get("LanguageSetting"), "es-ES")

  def test_compile_only_preserves_build_only_entry(self):
    with patch.dict(os.environ, SP_C3_COMPILE_ONLY="1"), patch.object(host_launch, "seed_developer_defaults") as seed:
      self.assertEqual(host_launch.main(["large", "--any-ui-arg"]), 0)
      seed.assert_not_called()

  def test_recorded_hardware_identity_requires_private_host_replay(self):
    from openpilot.common.hardware.pc.hardware import HardwarePc
    hardware = HardwarePc()
    with patch.dict(os.environ, SP_HOST_RUNTIME="1", SP_REPLAY_DEVICE_TYPE="tizi", OPENPILOT_PREFIX="replay-device"):
      self.assertEqual(hardware.get_device_type(), "tizi")
      os.environ["OPENPILOT_PREFIX"] = "d"
      self.assertEqual(hardware.get_device_type(), "pc")
      os.environ["OPENPILOT_PREFIX"] = "replay-device"
      os.environ["SP_REPLAY_DEVICE_TYPE"] = "unknown"
      self.assertEqual(hardware.get_device_type(), "pc")
