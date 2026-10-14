"""Exercise real hardware startup without importing hardware/native modules."""
import ast
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call


SOURCE = Path(__file__).resolve().parents[1] / "hardware.py"


def startup(device="mici", pid="322\n", status="Name:\tspi0\nPPid:\t2\n"):
  tree = ast.parse(SOURCE.read_text())
  cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "HardwareComma")
  method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "initialize_hardware")
  events = Mock()
  events.pgrep.return_value = pid
  events.status.return_value = status
  commands = SimpleNamespace(check_output=events.pgrep, check_call=events.command, call=events.command,
                             run=events.run, CalledProcessError=subprocess.CalledProcessError)
  namespace = {"subprocess": commands, "Path": lambda path: SimpleNamespace(read_text=lambda: events.status(path)),
               "affine_irq": events.irq, "gpio_init": events.gpio_init, "gpio_set": events.gpio_set,
               "GPIO": SimpleNamespace(SOM_ST_IO="fan"), "sudo_write": events.write, "print": events.error}
  exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), "exec"), namespace)
  hardware = SimpleNamespace(get_device_type=lambda: device,
                             amplifier=SimpleNamespace(initialize_configuration=events.amplifier))
  return lambda: namespace[method.name](hardware), events


class TestSpiWorkerPriority(unittest.TestCase):
  def test_spi_worker_outranks_actual_native_clients(self):
    main = (SOURCE.parents[3] / "selfdrive/pandad/main.cc").read_text()
    client_priority = int(re.search(r"util::set_realtime_priority\((\d+)\)", main).group(1))
    for device in ("tizi", "mici"):
      with self.subTest(device=device):
        initialize, events = startup(device)
        initialize()
        priority = next(c.args[0][4] for c in events.command.call_args_list if c.args[0][1] == "chrt")
        self.assertGreater(int(priority), client_priority,
                           "A deferred SPI completion must preempt the client/competing planner on core 3")

  def test_usb_device_keeps_existing_worker_priority(self):
    initialize, events = startup("tici")
    initialize()
    self.assertIn(call(["sudo", "chrt", "-f", "-p", "1", "322"]), events.command.call_args_list)

  def test_unknown_device_does_not_receive_high_priority(self):
    initialize, events = startup("unknown")
    initialize()
    self.assertIn(call(["sudo", "chrt", "-f", "-p", "1", "322"]), events.command.call_args_list)

  def test_affinity_succeeds_before_priority_is_raised(self):
    initialize, events = startup()
    initialize()
    self.assertEqual(events.command.call_args_list,
                     [call(["sudo", "taskset", "-pc", "3", "322"]),
                      call(["sudo", "chrt", "-f", "-p", "55", "322"])])

  def test_lookup_uses_exact_thread_name(self):
    initialize, events = startup()
    initialize()
    events.pgrep.assert_called_once_with(["pgrep", "-x", "spi0"], encoding="utf8")
    events.status.assert_called_once_with("/proc/322/status")

  def test_ambiguous_or_malformed_pid_is_rejected(self):
    for pid in ("322\n455\n", "", "322 xyz", "-1", "1; true"):
      with self.subTest(pid=pid):
        initialize, events = startup(pid=pid)
        initialize()
        events.command.assert_not_called()
        events.status.assert_not_called()
        events.error.assert_called_once()

  def test_a_userspace_namesake_is_not_promoted(self):
    initialize, events = startup(status="Name:\tspi0\nPPid:\t184\n")
    initialize()
    events.command.assert_not_called()
    events.error.assert_called_once()

  def test_a_reused_pid_is_not_promoted(self):
    initialize, events = startup(status="Name:\tother_worker\nPPid:\t2\n")
    initialize()
    events.command.assert_not_called()
    events.error.assert_called_once()

  def test_missing_kernel_identity_is_not_promoted(self):
    for status in ("Name:\tspi0\n", "PPid:\t2\n", "", "malformed"):
      with self.subTest(status=status):
        initialize, events = startup(status=status)
        initialize()
        events.command.assert_not_called()
        events.error.assert_called_once()

  def test_worker_disappearing_does_not_abort_other_startup(self):
    initialize, events = startup()
    events.status.side_effect = FileNotFoundError()
    initialize()
    events.command.assert_not_called()
    events.error.assert_called_once()
    events.gpio_set.assert_called_once_with("fan", True)

  def test_missing_worker_preserves_failure_containment(self):
    initialize, events = startup()
    events.pgrep.side_effect = subprocess.CalledProcessError(1, ["pgrep", "-x", "spi0"])
    initialize()
    events.command.assert_not_called()
    events.error.assert_called_once()

  def test_failed_affinity_never_raises_worker_priority(self):
    initialize, events = startup()
    events.command.side_effect = subprocess.CalledProcessError(1, "taskset")
    initialize()
    self.assertEqual(events.command.call_args_list, [call(["sudo", "taskset", "-pc", "3", "322"])])
    events.error.assert_called_once()

  def test_failed_priority_command_preserves_failure_containment(self):
    initialize, events = startup()
    events.command.side_effect = [0, subprocess.CalledProcessError(1, "chrt")]
    initialize()
    self.assertEqual(len(events.command.call_args_list), 2)
    events.error.assert_called_once()

  def test_existing_gpio_amplifier_and_transport_irqs_are_preserved(self):
    for device in ("tici", "tizi", "mici"):
      with self.subTest(device=device):
        initialize, events = startup(device)
        initialize()
        events.amplifier.assert_called_once_with(device)
        events.gpio_init.assert_called_once_with("fan", True)
        events.gpio_set.assert_called_once_with("fan", True)
        expected = [call(1, "msm_vidc"), call(1, "i2c_geni"), call(5, "fts_ts"),
                    call(5, "msm_drm"), call(3, "spi_geni")]
        if device == "tici":
          expected += [call(3, "xhci-hcd:usb3"), call(3, "xhci-hcd:usb1")]
        self.assertEqual(events.irq.call_args_list, expected)
        events.error.assert_not_called()


if __name__ == "__main__":
  unittest.main()
