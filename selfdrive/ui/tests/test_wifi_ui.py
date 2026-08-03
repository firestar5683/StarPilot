import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "mici" / "layouts" / "settings" / "network" / "action_state.py"
SPEC = importlib.util.spec_from_file_location("wifi_ui_action_state_under_test", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
should_show_forget_button = MODULE.should_show_forget_button


def test_should_show_forget_button_for_saved_network():
  assert should_show_forget_button(is_tethering=False, is_forgetting=False, is_saved=True,
                                   wrong_password=False, is_connecting=False)


def test_should_show_forget_button_while_connecting():
  assert should_show_forget_button(is_tethering=False, is_forgetting=False, is_saved=False,
                                   wrong_password=False, is_connecting=True)


def test_should_hide_forget_button_for_unsaved_network():
  assert not should_show_forget_button(is_tethering=False, is_forgetting=False, is_saved=False,
                                       wrong_password=False, is_connecting=False)


def test_should_hide_forget_button_for_tethering_forgetting_and_wrong_password():
  assert not should_show_forget_button(is_tethering=True, is_forgetting=False, is_saved=True,
                                       wrong_password=False, is_connecting=False)
  assert not should_show_forget_button(is_tethering=False, is_forgetting=True, is_saved=True,
                                       wrong_password=False, is_connecting=False)
  assert not should_show_forget_button(is_tethering=False, is_forgetting=False, is_saved=True,
                                       wrong_password=True, is_connecting=False)
