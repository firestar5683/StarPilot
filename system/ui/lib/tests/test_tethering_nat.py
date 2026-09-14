import subprocess
import sys
import types
import unittest
from unittest import mock

# swaglog pulls in compiled msgq, unavailable in some checkouts; stub it
if "openpilot.common.swaglog" not in sys.modules:
  try:
    import openpilot.common.swaglog  # noqa: F401
  except ImportError:
    stub = types.ModuleType("openpilot.common.swaglog")
    stub.cloudlog = mock.MagicMock()
    sys.modules["openpilot.common.swaglog"] = stub

from openpilot.system.ui.lib import tethering_nat


def _run_ok(cmd, **kwargs):
  return subprocess.CompletedProcess(cmd, 0, "", "")


class TestTetheringNat(unittest.TestCase):

  def test_subnet_cidr(self):
    self.assertEqual(tethering_nat._subnet_cidr("10.42.0.1", 24), "10.42.0.0/24")
    self.assertEqual(tethering_nat._subnet_cidr("192.168.43.1", 24), "192.168.43.0/24")
    self.assertEqual(tethering_nat._subnet_cidr("10.99.62.240", 24), "10.99.62.0/24")
    self.assertEqual(tethering_nat._subnet_cidr("172.16.5.9", 12), "172.16.0.0/12")
    self.assertEqual(tethering_nat._subnet_cidr("8.8.8.8", 32), "8.8.8.8/32")
    self.assertIsNone(tethering_nat._subnet_cidr("300.1.1.1", 24))
    self.assertIsNone(tethering_nat._subnet_cidr("1.2.3", 24))

  def test_interface_subnet_parses_ip_output(self):
    result = subprocess.CompletedProcess(
      [], 0, "11: wlan0    inet 10.42.0.1/24 brd 10.42.0.255 scope global wlan0\n", "")
    with mock.patch.object(subprocess, "run", return_value=result):
      self.assertEqual(tethering_nat._interface_subnet("wlan0"), "10.42.0.0/24")

  def test_interface_subnet_no_address(self):
    result = subprocess.CompletedProcess([], 0, "", "")
    with mock.patch.object(subprocess, "run", return_value=result):
      self.assertIsNone(tethering_nat._interface_subnet("wlan0"))

  def test_hotspot_subnets_live_first_then_candidates(self):
    with mock.patch.object(tethering_nat, "_interface_subnet", return_value="10.42.0.0/24"):
      self.assertEqual(tethering_nat.hotspot_subnets(),
                       ("10.42.0.0/24", "192.168.43.0/24"))
    with mock.patch.object(tethering_nat, "_interface_subnet", return_value=None):
      self.assertEqual(tethering_nat.hotspot_subnets(),
                       ("10.42.0.0/24", "192.168.43.0/24"))
    with mock.patch.object(tethering_nat, "_interface_subnet", return_value="192.168.0.0/24"):
      self.assertEqual(tethering_nat.hotspot_subnets(),
                       ("192.168.0.0/24", "10.42.0.0/24", "192.168.43.0/24"))

  def test_ensure_noops_without_iptables(self):
    with mock.patch.object(tethering_nat.shutil, "which", return_value=None):
      self.assertFalse(tethering_nat.ensure_tethering_nat())

  def test_ensure_applies_rules_idempotently(self):
    calls = []

    def fake_run(cmd, **kwargs):
      calls.append(cmd)
      return subprocess.CompletedProcess(cmd, 0, "", "")

    with mock.patch.object(tethering_nat.shutil, "which", return_value="/usr/sbin/iptables-legacy"), \
         mock.patch.object(tethering_nat.subprocess, "run", side_effect=fake_run), \
         mock.patch.object(tethering_nat, "_interface_subnet", return_value=None):
      self.assertTrue(tethering_nat.ensure_tethering_nat())

    sysctls = [c for c in calls if "sysctl" in c]
    self.assertEqual(len(sysctls), 1)
    self.assertIn("net.ipv4.ip_forward=1", sysctls[0])

    # check-only passes: nothing re-added; 3 checks per subnet, 2 candidate subnets
    ipt = [c for c in calls if "iptables-legacy" in c]
    self.assertEqual(len(ipt), 6)
    self.assertTrue(all("-C" in c for c in ipt))

  def test_ensure_adds_when_check_fails(self):
    calls = []

    def fake_run(cmd, **kwargs):
      calls.append(cmd)
      # sudo checks fail (rule missing), sudo adds succeed
      returncode = 1 if "-C" in cmd else 0
      return subprocess.CompletedProcess(cmd, returncode, "", "")

    with mock.patch.object(tethering_nat.shutil, "which", return_value="/usr/sbin/iptables-legacy"), \
         mock.patch.object(tethering_nat.subprocess, "run", side_effect=fake_run), \
         mock.patch.object(tethering_nat, "_interface_subnet", return_value=None):
      self.assertTrue(tethering_nat.ensure_tethering_nat())

    ipt = [c for c in calls if "iptables-legacy" in c]
    self.assertEqual(len(ipt), 12)  # check+add per rule, 3 rules x 2 subnets
    self.assertEqual(len([c for c in ipt if "-A" in c]), 6)

  def test_ensure_excludes_live_subnet_when_not_hotspot(self):
    calls = []

    def fake_run(cmd, **kwargs):
      calls.append(cmd)
      return subprocess.CompletedProcess(cmd, 0, "", "")

    with mock.patch.object(tethering_nat.shutil, "which", return_value="/usr/sbin/iptables-legacy"), \
         mock.patch.object(tethering_nat.subprocess, "run", side_effect=fake_run), \
         mock.patch.object(tethering_nat, "_interface_subnet", return_value="10.99.62.0/24"):
      self.assertTrue(tethering_nat.ensure_tethering_nat(include_live_subnet=False))

    ipt = [c for c in calls if "iptables-legacy" in c]
    self.assertFalse(any("10.99.62.0/24" in " ".join(c) for c in ipt))


if __name__ == "__main__":
  unittest.main()
