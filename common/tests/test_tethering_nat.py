import struct
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

from openpilot.common import tethering_nat


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
    self.assertIsNone(tethering_nat._subnet_cidr("-1.2.3.4", 24))
    self.assertIsNone(tethering_nat._subnet_cidr("1.2.three.4", 24))
    self.assertIsNone(tethering_nat._subnet_cidr("1.2.3.4", True))

  def test_interface_subnet_parses_ip_output(self):
    result = subprocess.CompletedProcess(
      [], 0, "11: wlan0    inet 10.42.0.1/24 brd 10.42.0.255 scope global wlan0\n", "")
    with mock.patch.object(subprocess, "run", return_value=result):
      self.assertEqual(tethering_nat._interface_subnet("wlan0"), "10.42.0.0/24")

  def test_interface_subnet_no_address(self):
    result = subprocess.CompletedProcess([], 0, "", "")
    with mock.patch.object(subprocess, "run", return_value=result):
      self.assertIsNone(tethering_nat._interface_subnet("wlan0"))

  def test_interface_subnet_ignores_malformed_address_lines(self):
    result = subprocess.CompletedProcess([], 0, "11: wlan0 inet\n11: wlan0 inet not-an-address\n", "")
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
    with mock.patch.object(tethering_nat.shutil, "which", return_value=None), \
         mock.patch.object(tethering_nat.os, "access", return_value=False):
      self.assertFalse(tethering_nat.ensure_tethering_nat())

  def test_iptables_binary_falls_back_to_absolute(self):
    # daemons run with a PATH lacking /usr/sbin; shutil.which() alone fails
    with mock.patch.object(tethering_nat.shutil, "which", return_value=None), \
         mock.patch.object(tethering_nat.os, "access", return_value=True):
      self.assertEqual(tethering_nat.iptables_binary(), tethering_nat.IPTABLES_ABSOLUTE)
    with mock.patch.object(tethering_nat.shutil, "which", return_value="/usr/bin/iptables-legacy"):
      self.assertEqual(tethering_nat.iptables_binary(), "/usr/bin/iptables-legacy")
    with mock.patch.object(tethering_nat.shutil, "which", return_value=None), \
         mock.patch.object(tethering_nat.os, "access", return_value=False):
      self.assertIsNone(tethering_nat.iptables_binary())

  def test_ensure_uses_absolute_path_when_path_lacks_usr_sbin(self):
    calls = []

    def fake_run(cmd, **kwargs):
      calls.append(cmd)
      return subprocess.CompletedProcess(cmd, 0, "", "")

    with mock.patch.object(tethering_nat.shutil, "which", return_value=None), \
         mock.patch.object(tethering_nat.os, "access", return_value=True), \
         mock.patch.object(tethering_nat.subprocess, "run", side_effect=fake_run), \
         mock.patch.object(tethering_nat, "_interface_subnet", return_value=None):
      self.assertTrue(tethering_nat.ensure_tethering_nat())

    ipt = [c for c in calls if any("iptables-legacy" in part for part in c)]
    self.assertTrue(ipt)
    self.assertTrue(all(c[2] == tethering_nat.IPTABLES_ABSOLUTE for c in ipt))

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
    ipt = [c for c in calls if any("iptables-legacy" in part for part in c)]
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

    ipt = [c for c in calls if any("iptables-legacy" in part for part in c)]
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

    ipt = [c for c in calls if any("iptables-legacy" in part for part in c)]
    self.assertFalse(any("10.99.62.0/24" in " ".join(c) for c in ipt))

  def test_hotspot_address_active(self):
    with mock.patch.object(tethering_nat, "_interface_subnet", return_value="10.42.0.0/24"):
      self.assertTrue(tethering_nat.hotspot_address_active())
    with mock.patch.object(tethering_nat, "_interface_subnet", return_value="10.99.62.0/24"):
      self.assertFalse(tethering_nat.hotspot_address_active())
    with mock.patch.object(tethering_nat, "_interface_subnet", return_value=None):
      self.assertFalse(tethering_nat.hotspot_address_active())

  @staticmethod
  def _nlmsg(msg_type: int, family: int, ifindex: int) -> bytes:
    header = struct.pack("<IHHII", 24, msg_type, 0, 0, 0)
    ifaddrmsg = struct.pack("<BBBBI", family, 24, 0, 0, ifindex)
    return header + ifaddrmsg

  def test_iter_addr_events_matches_interface(self):
    ifindex = 11
    data = (self._nlmsg(tethering_nat.RTM_NEWADDR, tethering_nat.AF_INET, ifindex) +
            self._nlmsg(tethering_nat.RTM_NEWADDR, tethering_nat.AF_INET, 3) +   # other iface
            self._nlmsg(tethering_nat.RTM_DELADDR, 10, ifindex) +                # IPv6
            self._nlmsg(16, tethering_nat.AF_INET, ifindex))                     # RTM_NEWLINK
    self.assertEqual(list(tethering_nat._iter_addr_events(data, ifindex)), [tethering_nat.RTM_NEWADDR])

  def test_iter_addr_events_truncated_stream(self):
    data = self._nlmsg(tethering_nat.RTM_NEWADDR, tethering_nat.AF_INET, 1)[:-4]
    self.assertEqual(list(tethering_nat._iter_addr_events(data, 1)), [])

  class _StopMonitor(Exception):
    pass

  def test_monitor_ensures_on_hotspot_addr_event(self):
    events = []

    class FakeSock:
      def __enter__(self):
        return self

      def __exit__(self, *a):
        return False

      def bind(self, *a):
        pass

      def setsockopt(self, *a):
        pass

      def recv(self, n):
        events.append("recv")
        if len(events) == 1:
          return TestTetheringNat._nlmsg(tethering_nat.RTM_NEWADDR, tethering_nat.AF_INET, 11)
        raise TestTetheringNat._StopMonitor()

    runner = tethering_nat.tethering_nat_thread("wlan0")
    with mock.patch.object(tethering_nat.socket, "if_nametoindex", return_value=11), \
         mock.patch.object(tethering_nat.socket, "socket", return_value=FakeSock()), \
         mock.patch.object(tethering_nat, "hotspot_address_active", return_value=True), \
         mock.patch.object(tethering_nat, "ensure_tethering_nat", side_effect=lambda *a, **k: events.append("ensure")) as m:
      with self.assertRaises(TestTetheringNat._StopMonitor):
        runner()
      m.assert_called_once()
      self.assertIn("ensure", events)

  def test_monitor_ignores_client_addr_events(self):
    class FakeSock:
      def __enter__(self):
        return self

      def __exit__(self, *a):
        return False

      def bind(self, *a):
        pass

      def setsockopt(self, *a):
        pass

      def recv(self, n):
        raise TestTetheringNat._StopMonitor()

    runner = tethering_nat.tethering_nat_thread("wlan0")
    with mock.patch.object(tethering_nat.socket, "if_nametoindex", return_value=11), \
         mock.patch.object(tethering_nat.socket, "socket", return_value=FakeSock()), \
         mock.patch.object(tethering_nat, "hotspot_address_active", return_value=False), \
         mock.patch.object(tethering_nat, "ensure_tethering_nat", side_effect=lambda *a, **k: None) as m:
      with self.assertRaises(TestTetheringNat._StopMonitor):
        runner()
      m.assert_not_called()  # hotspot not active: neither startup nor any event

  def test_monitor_covers_hotspot_already_up_at_start(self):
    class FakeSock:
      def __enter__(self):
        return self

      def __exit__(self, *a):
        return False

      def bind(self, *a):
        pass

      def setsockopt(self, *a):
        pass

      def recv(self, n):
        # unrelated event (other interface), then stop
        return TestTetheringNat._nlmsg(tethering_nat.RTM_NEWADDR, tethering_nat.AF_INET, 3)

    runner = tethering_nat.tethering_nat_thread("wlan0")
    with mock.patch.object(tethering_nat.socket, "if_nametoindex", return_value=11), \
         mock.patch.object(tethering_nat.socket, "socket", return_value=FakeSock()), \
         mock.patch.object(tethering_nat, "hotspot_address_active", return_value=True), \
         mock.patch.object(tethering_nat, "ensure_tethering_nat", side_effect=lambda *a, **k: None) as m:
      with mock.patch.object(tethering_nat, "_interface_subnet", return_value="10.42.0.0/24"):
        # second recv stops the loop
        orig = FakeSock.recv
        FakeSock.recv = lambda self, n: (_ for _ in ()).throw(TestTetheringNat._StopMonitor())
        try:
          with self.assertRaises(TestTetheringNat._StopMonitor):
            runner()
          m.assert_called_once()
        finally:
          FakeSock.recv = orig


if __name__ == "__main__":
  unittest.main()
