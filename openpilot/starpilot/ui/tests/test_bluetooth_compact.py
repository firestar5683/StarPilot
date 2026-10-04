"""C4 Bluetooth delegates mutations to the parked owner off the render thread."""
from unittest.mock import patch


from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace as NS
import time
import unittest
from unittest.mock import Mock

from openpilot.starpilot.ui.bluetooth_compact import BluetoothCompact, device_label
from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.settings_state import Destination, SettingsInput, SettingsState


class TestBluetoothCompact(unittest.TestCase):
  def test_device_names_are_bounded_and_unpaired_device_starts_owned_pairing(self):
    self.assertEqual(device_label({"name": "A\nB\x00", "address": "AA:BB:CC:DD:EE:FF"}), "AB")
    page = BluetoothCompact.__new__(BluetoothCompact)
    page.status = {"devices": [{"address": "AA:BB:CC:DD:EE:FF", "name": "New", "paired": False}]}
    with patch.object(page, "_request") as request:
      page._open_device("AA:BB:CC:DD:EE:FF")
    request.assert_called_once_with("pair", address="AA:BB:CC:DD:EE:FF")

  def pair_page(self, kind="confirmation", value="123456"):
    class Button:
      def __init__(self, label, subtitle="", *args, **kwargs):
        self.label, self.subtitle, self.click = label, subtitle, None
      def set_click_callback(self, callback):
        self.click = callback
      def set_enabled(self, callback):
        self.enabled = callback

    page = BluetoothCompact.__new__(BluetoothCompact)
    page.session = ('compact', 'one')
    page.active = True
    page.status = {'available': True, 'parked': True, 'powered': True, 'devices': [],
                   'pairing': {'address': 'AA:BB:CC:DD:EE:FF', 'state': 'pairing',
                               'prompt': {'id': 'a' * 32, 'kind': kind, 'value': value, 'displayOnly': False}}}
    page.pending = None
    page.queued = None
    page.return_to_root = False
    page.icon = object()
    page.pair_dialog = None
    page.pair_dialog_id = None
    self.enterContext(patch.object(page, 'executor', NS(submit=Mock(return_value=Future())), create=True))
    self.enterContext(patch.object(page, 'owner', NS(request=Mock()), create=True))
    self.enterContext(patch('openpilot.starpilot.ui.bluetooth_compact.BigButton', Button))
    self.enterContext(patch('openpilot.starpilot.ui.bluetooth_compact.GreyBigButton', Button))
    self.enterContext(patch.object(BluetoothCompact, '_rebuild'))
    return page

  def test_confirmation_requires_touch_then_explicit_slider_and_current_prompt(self):
    page = self.pair_page()
    dialogs = []
    def dialog(title, _icon, callback):
      made = NS(title=title, confirm=callback)
      dialogs.append(made)
      return made
    with patch('openpilot.starpilot.ui.bluetooth_compact.BigConfirmationDialog', dialog), \
         patch('openpilot.starpilot.ui.bluetooth_compact.gui_app.push_widget') as push:
      cards = page._pairing_cards()
      self.assertEqual(next(card.subtitle for card in cards if card.label == 'match this code'), '123456')
      confirm = next(card for card in cards if card.label == 'confirm match')
      self.assertTrue(confirm.enabled())
      page.executor.submit.assert_not_called()
      confirm.click()
      self.assertIn('123456', dialogs[0].title)
      push.assert_called_once_with(dialogs[0])
      page.executor.submit.assert_not_called()
      page.status['pairing']['prompt'] = {**page.status['pairing']['prompt'], 'id': 'b' * 32}
      dialogs[0].confirm()
      page.executor.submit.assert_not_called()
      page.status['pairing']['prompt']['id'] = 'a' * 32
      dialogs[0].confirm()
      page.executor.submit.assert_called_once_with(page.owner.request, 'pairing_response', address=None,
                                                    session=page.session, prompt_id='a' * 32, accepted=True, value='')

  def test_passkey_input_is_masked_bounded_and_cancel_uses_same_session(self):
    page = self.pair_page('passkey', '')
    dialogs = []
    def input_dialog(hint, **kwargs):
      made = NS(hint=hint, **kwargs)
      dialogs.append(made)
      return made
    with patch('openpilot.starpilot.ui.bluetooth_compact.BigInputDialog', input_dialog), \
         patch('openpilot.starpilot.ui.bluetooth_compact.gui_app.push_widget'):
      cards = page._pairing_cards()
      next(card for card in cards if card.label == 'enter passkey').click()
      self.assertTrue(dialogs[0].password_mode)
      self.assertFalse(dialogs[0].text_validator('1234567'))
      self.assertFalse(dialogs[0].text_validator('abc'))
      self.assertTrue(dialogs[0].text_validator('123456'))
      dialogs[0].confirm_callback('123456')
    page.executor.submit.assert_called_once_with(page.owner.request, 'pairing_response', address=None,
                                                  session=page.session, prompt_id='a' * 32,
                                                  accepted=True, value='123456')
    page.pending = None
    page.queued = None
    next(card for card in page._pairing_cards() if card.label == 'cancel pairing').click()
    page.executor.submit.assert_called_with(page.owner.request, 'cancel_pair', address=None,
                                             session=page.session, prompt_id=None, accepted=None, value='')

  def test_pin_input_is_masked_and_rejects_control_characters(self):
    page = self.pair_page('pin', '')
    with patch('openpilot.starpilot.ui.bluetooth_compact.BigInputDialog', side_effect=lambda *args, **kwargs: NS(**kwargs)), \
         patch('openpilot.starpilot.ui.bluetooth_compact.gui_app.push_widget') as push:
      next(card for card in page._pairing_cards() if card.label == 'enter PIN').click()
    dialog = push.call_args.args[0]
    self.assertTrue(dialog.password_mode)
    self.assertTrue(dialog.text_validator('0000'))
    self.assertFalse(dialog.text_validator('a\n'))
    self.assertFalse(dialog.text_validator('x' * 17))

  def test_dismissed_page_revokes_pair_session_before_worker_completion(self):
    page = self.pair_page()
    session = page.session
    page.pending = Future()
    page.operation = 'pair'
    page.pending_session = session
    page.executor.submit.return_value = Future()
    page.executor.shutdown = Mock()
    page.owner.close = Mock()
    with patch('openpilot.starpilot.ui.bluetooth_compact.gui_app.remove_nav_stack_tick'), \
         patch('openpilot.starpilot.ui.bluetooth_compact.NavScroller.hide_event'):
      page.hide_event()
    self.assertFalse(page.active)
    self.assertIsNone(page.session)
    self.assertIsNone(page.status)
    page.active = True
    page.session = ('compact', 'two')
    page.executor = None
    page.pending.set_result({'available': True, 'parked': True, 'pairing': {'state': 'pairing'}})
    with patch.object(page, '_snapshot') as snapshot, \
         patch('openpilot.starpilot.ui.bluetooth_compact.gui_app.push_widget') as push:
      page._tick()
    self.assertIsNone(page.status)
    snapshot.assert_called_once_with()
    push.assert_not_called()

  def test_owner_operation_is_submitted_to_worker_and_result_updates_on_tick(self):
    page = BluetoothCompact.__new__(BluetoothCompact)
    future = Future()
    owner = NS(request=Mock())
    self.enterContext(patch.object(page, "owner", owner, create=True))
    self.enterContext(patch.object(page, "executor", NS(submit=Mock(return_value=future)), create=True))
    page.status = {"available": True, "parked": True, "powered": False}
    page.pending = None
    page.queued = None
    page.next_refresh = float("inf")
    page.return_to_root = False
    with patch.object(BluetoothCompact, "_rebuild") as rebuild:
      page._request("power", enabled=True)
      page.executor.submit.assert_called_once_with(owner.request, "power", address=None, enabled=True)
      owner.request.assert_not_called()
      self.assertIs(page.pending, future)
      result = {"available": True, "parked": True, "powered": True, "devices": []}
      future.set_result(result)
      page._tick()
      self.assertEqual(page.status, result)
      self.assertIsNone(page.pending)
      self.assertEqual(rebuild.call_count, 2)

  def test_parked_status_blocks_submission_and_hide_closes_owner_on_worker(self):
    page = BluetoothCompact.__new__(BluetoothCompact)
    owner = NS(close=Mock(), request=Mock())
    self.enterContext(patch.object(page, "owner", owner, create=True))
    self.enterContext(patch.object(page, "executor", NS(submit=Mock(return_value=Future()), shutdown=Mock()), create=True))
    executor = page.executor
    page.status = {"available": True, "parked": False}
    page.pending = None
    page.queued = None
    with patch.object(page, "_rebuild"):
      page._request("power", enabled=True)
    executor.submit.assert_not_called()
    with patch("openpilot.starpilot.ui.bluetooth_compact.gui_app.remove_nav_stack_tick"), \
         patch("openpilot.starpilot.ui.bluetooth_compact.NavScroller.hide_event"):
      page.hide_event()
    executor.submit.assert_called_once_with(owner.close)
    executor.shutdown.assert_called_once_with(wait=False, cancel_futures=False)
    self.assertIsNone(page.executor)

  def test_close_retires_worker_and_next_snapshot_recreates_it(self):
    page = BluetoothCompact.__new__(BluetoothCompact)
    owner = NS(close=Mock(), snapshot=Mock(return_value={"available": True, "parked": True}))
    self.enterContext(patch.object(page, "owner", owner, create=True))
    page.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="c4-bluetooth-test")
    old_executor = page.executor
    page.pending = old_executor.submit(lambda: None)
    page.pending.result(timeout=1)
    page.operation = "snapshot"
    page.status = {"available": True, "parked": True}
    page.queued = None
    page.return_to_root = False
    with patch("openpilot.starpilot.ui.bluetooth_compact.gui_app.remove_nav_stack_tick"), \
         patch("openpilot.starpilot.ui.bluetooth_compact.NavScroller.hide_event"):
      page.hide_event()
    self.assertIsNone(page.executor)
    page.pending.result(timeout=1)
    for _ in range(50):
      if not any(thread.is_alive() for thread in old_executor._threads):
        break
      time.sleep(0.01)
    self.assertFalse(any(thread.is_alive() for thread in old_executor._threads))
    page.pending = None
    page._snapshot()
    self.assertIsNot(page.executor, old_executor)
    page.pending.result(timeout=1)
    page.executor.shutdown(wait=True)

  def test_action_clicked_during_refresh_is_queued_without_blocking_ui(self):
    page = BluetoothCompact.__new__(BluetoothCompact)
    refreshing, action = Future(), Future()
    owner = NS(request=Mock())
    self.enterContext(patch.object(page, "owner", owner, create=True))
    self.enterContext(patch.object(page, "executor", NS(submit=Mock(return_value=action)), create=True))
    page.status = {"available": True, "parked": True, "powered": True}
    page.pending = refreshing
    page.operation = "snapshot"
    page.queued = None
    page.return_to_root = False
    page.next_refresh = float("inf")
    with patch.object(BluetoothCompact, "_rebuild"):
      page._request("scan")
      page.executor.submit.assert_not_called()
      refreshing.set_result(page.status)
      page._tick()
    page.executor.submit.assert_called_once_with(owner.request, "scan", address=None, enabled=None)
    self.assertIs(page.pending, action)
    self.assertIsNone(page.queued)

  def test_main_menu_opens_bluetooth_panel(self):
    from openpilot.starpilot.ui import runtime_app
    layout = runtime_app.StarMiciMainLayout.__new__(runtime_app.StarMiciMainLayout)
    object.__setattr__(layout, "_compact_panels", {})
    panel = Mock()
    object.__setattr__(layout, "star", NS(connectivity_allowed=Mock(return_value=True)))
    with patch("openpilot.starpilot.ui.bluetooth_compact.BluetoothCompact", return_value=panel) as built, \
         patch.object(runtime_app.gui_app, "push_widget") as push:
      layout._open_compact_destination(Destination.BLUETOOTH)
      layout._open_compact_destination(Destination.BLUETOOTH)
    built.assert_called_once_with(layout.star.connectivity_allowed)
    self.assertEqual(push.call_count, 2)

  def test_firehose_is_not_a_compact_settings_destination(self):
    from openpilot.selfdrive.ui.mici.layouts.settings import developer
    self.assertFalse(hasattr(developer.DeveloperLayoutMici, "_open_firehose"))

  def test_paired_compact_menu_removes_pair_card_and_preserves_hit_targets(self):
    from openpilot.starpilot.ui.settings_state import compact_menu
    paired = SettingsState(paired=True)
    self.assertIn(Destination.PAIR, [item[0] for item in compact_menu(SettingsState())])
    self.assertNotIn(Destination.PAIR, [item[0] for item in compact_menu(paired)])
    self.assertEqual(len(compact_menu(SettingsState())) - len(compact_menu(paired)), 1)
    emitted = []
    touch = SettingsInput(Profile.COMPACT, emitted.append)
    index = next(i for i, item in enumerate(compact_menu(paired)) if item[0] == Destination.DEVELOPER)
    paired = replace(paired, compact_scroll_x=-422 * index)
    touch.press(45, 75, paired)
    touch.release(45, 75, paired)
    self.assertEqual(emitted[-1].destination.destination, Destination.DEVELOPER)
