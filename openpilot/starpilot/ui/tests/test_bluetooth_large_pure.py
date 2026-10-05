from typing import Any
import ast
from concurrent.futures import Future
from pathlib import Path
import re
import time
import unittest
import uuid


class Widget:
  def show_event(self):
    pass

  def hide_event(self):
    pass


class Scroller(Widget):
  def __init__(self, rows, **kwargs):
    self.rows = rows
    self.scroll_panel = Scroll()


class Row(tuple):
  def set_touch_valid_callback(self, callback):
    pass


class Scroll:
  def is_touch_valid(self):
    return True


class App:
  def __init__(self):
    self.widgets = []
    self.mouse_events = []
    self.ticks = []

  def add_nav_stack_tick(self, callback):
    self.ticks.append(callback)

  def remove_nav_stack_tick(self, callback):
    self.ticks.remove(callback)

  def push_widget(self, widget):
    self.widgets.append(widget)

  def get_active_widget(self):
    return self.widgets[-1] if self.widgets else None

  def pop_widget(self):
    self.widgets.pop()


class Executor:
  def __init__(self, **kwargs):
    self.jobs = []

  def submit(self, callback, *args, **kwargs):
    future = Future()
    self.jobs.append((future, callback, args, kwargs))
    return future

  def shutdown(self, **kwargs):
    pass


class Owner:
  def __init__(self, authority, session_valid):
    self.authority = authority
    self.session_valid = session_valid

  def snapshot(self, **kwargs):
    pass

  def request(self, *args, **kwargs):
    pass

  def close(self):
    pass


class Dialog:
  def __init__(self, *args, **kwargs):
    self.callback = kwargs.get('callback')
    self.text = ''

  def set_title(self, *args):
    pass

  def set_callback(self, callback):
    self.callback = callback

  def clear(self):
    self.text = ''


class TestBluetoothLarge(unittest.TestCase):
  def setUp(self):
    path = Path(__file__).parents[1] / 'bluetooth_large.py'
    tree = ast.parse(path.read_text())
    tree.body = [node for node in tree.body if not isinstance(node, (ast.Import, ast.ImportFrom))]
    self.app = App()
    scope: dict[str, Any] = {'Callable': object, 'Future': Future, 'ThreadPoolExecutor': Executor, 're': re, 'time': time, 'uuid': uuid,
                 'Widget': Widget, 'Scroller': Scroller, 'BluetoothOwner': Owner, 'BluetoothRejected': ValueError,
                 'BluetoothUnavailable': RuntimeError, 'gui_app': self.app, 'button_item': lambda *a, **kw: Row((a, kw)),
                 'text_item': lambda *a, **kw: Row((a, kw)), 'ConfirmDialog': Dialog, 'alert_dialog': Dialog,
                 'DialogResult': type('Result', (), {'CONFIRM': 1}), 'Keyboard': Dialog}
    tree.body.insert(0, ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0))
    exec(compile(ast.fix_missing_locations(tree), str(path), 'exec'), scope)
    self.panel_type = scope['BluetoothLarge']
    self.panel = self.panel_type(lambda: True)

  def test_constructor_with_menu_mouse_edge_creates_scroller(self):
    self.app.mouse_events = [object()]
    panel = self.panel_type(lambda: True)
    self.assertIsInstance(panel._scroller, Scroller)
    panel.show_event()
    panel.hide_event()

  def test_show_submits_snapshot_without_running_owner(self):
    self.panel.show_event()
    self.assertFalse(self.panel.pending.done())
    self.assertEqual(self.panel.executor.jobs[0][2], ())
    self.assertTrue(self.panel.owner.session_valid(self.panel.session))

  def test_open_powered_panel_scans_once_and_stops_on_hide(self):
    self.panel.show_event()
    self.panel.pending.set_result({'available': True, 'powered': True, 'parked': True, 'discovering': False})
    self.panel._tick()
    self.assertEqual(self.panel.operation, 'scan')
    self.panel.pending.set_result({'available': True, 'powered': True, 'parked': True, 'discovering': False})
    self.panel._tick()
    self.assertEqual(sum(job[2] == ('scan',) for job in self.panel.executor.jobs), 1)
    executor = self.panel.executor
    self.panel.hide_event()
    self.assertEqual(executor.jobs[-1][1], self.panel.owner.close)

  def test_pairing_prompt_opens_once_and_expired_prompt_is_retired(self):
    prompt = {'id': 'a' * 32, 'kind': 'confirmation', 'value': '123456', 'displayOnly': False}
    status: dict[str, Any] = {'available': True, 'powered': True, 'parked': True, 'discovering': False,
              'pairing': {'state': 'pairing', 'prompt': prompt}}
    self.panel.show_event()
    self.panel.pending.set_result(status)
    self.panel._tick()
    self.assertEqual(len(self.app.widgets), 1)
    self.panel._snapshot()
    self.panel.pending.set_result(status)
    self.panel._tick()
    self.assertEqual(len(self.app.widgets), 1)
    self.panel._snapshot()
    self.panel.pending.set_result({'available': True, 'powered': True, 'parked': True})
    self.panel._tick()
    self.assertEqual(len(self.app.widgets), 0)

  def test_pin_cancel_rejects_prompt_and_clears_keyboard(self):
    prompt = {'id': 'a' * 32, 'kind': 'pin', 'value': '', 'displayOnly': False}
    self.panel.show_event()
    self.panel.pending.set_result({'available': True, 'powered': True, 'parked': True,
                                   'pairing': {'state': 'pairing', 'prompt': prompt}})
    self.panel._tick()
    keyboard = self.app.widgets[-1]
    keyboard.text = '1234'
    keyboard.callback(0)
    self.assertEqual(keyboard.text, '')
    job = self.panel.executor.jobs[-1]
    self.assertEqual(job[2], ('pairing_response',))
    self.assertFalse(job[3]['accepted'])
    self.assertEqual(job[3]['value'], '')

  def test_named_devices_and_disconnect_forget_presented(self):
    self.panel.status = {'available': True, 'powered': True, 'parked': True, 'devices': [
      {'address': 'AA:BB', 'name': 'Headphones', 'paired': True, 'connected': True}]}
    self.panel._scroller = None
    self.panel._rebuild()
    rows = self.panel._scroller.rows
    self.assertIn(('Headphones', 'Disconnect'), [row[0] for row in rows])
    self.assertIn(('Forget Headphones', 'Forget'), [row[0] for row in rows])

  def test_request_waits_for_snapshot_then_submits_async(self):
    self.panel.show_event()
    self.panel.status = {'available': True, 'powered': True, 'parked': True}
    self.panel._signature = repr((False, True, True, True, None, None, None, ()))
    self.panel._request('connect', address='AA:BB')
    self.assertIsNotNone(self.panel.queued)
    self.panel.pending.set_result(self.panel.status)
    self.panel._tick()
    self.assertEqual(self.panel.operation, 'connect')
    self.assertEqual(self.panel.executor.jobs[-1][2], ('connect',))
    self.assertFalse(self.panel.pending.done())

  def test_refresh_preserves_scroller_and_defers_active_touch(self):
    self.panel.status = {'available': True, 'powered': True, 'parked': True, 'devices': []}
    self.panel._rebuild()
    scroller = self.panel._scroller
    scroll = scroller.scroll_panel
    updated: dict[str, Any] = dict(self.panel.status)
    updated['unshownTelemetry'] = 123
    self.panel.status = updated
    self.panel._rebuild()
    self.assertIs(self.panel._scroller, scroller)
    self.panel._touch_held = True
    self.panel.status['powered'] = False
    self.panel._rebuild()
    self.assertIs(self.panel._scroller, scroller)
    self.panel._touch_held = False
    self.panel._rebuild()
    self.assertIs(self.panel._scroller.scroll_panel, scroll)

  def test_paginated_host_can_refresh_rows_without_rendering_the_native_scroller(self):
    self.panel.status = {'available': True, 'powered': True, 'parked': True, 'devices': []}
    self.panel._update_state()
    self.assertEqual(len(self.panel._scroller.rows), 2)
    self.panel._touch_held = True
    self.app.mouse_events = [type('Event', (), {'slot': 0, 'left_down': False})()]
    self.panel._update_state()
    self.assertFalse(self.panel._touch_held)
    self.app.mouse_events = []
    self.panel.status['powered'] = False
    self.panel._update_state()
    self.assertEqual(len(self.panel._scroller.rows), 1)

  def test_unnamed_unpaired_devices_not_presented(self):
    self.panel.status = {'available': True, 'powered': True, 'parked': True, 'devices': [
      {'address': 'AA:BB:CC:DD:EE:FF', 'name': 'AA:BB:CC:DD:EE:FF', 'paired': False},
      {'address': '11:22:33:44:55:66', 'name': 'Bluetooth Device · 55:66', 'paired': False}]}
    self.panel._rebuild()
    self.assertEqual(len(self.panel._scroller.rows), 2)

  def test_hidden_session_cannot_confirm_forget(self):
    self.panel.show_event()
    calls = []
    self.panel._confirm('Forget?', lambda: calls.append(True))
    dialog = self.app.widgets[-1]
    self.panel.hide_event()
    dialog.callback(1)
    self.assertEqual(calls, [])
    self.assertFalse(self.panel.owner.session_valid(('large', 'old')))

  def test_stale_completion_not_applied_on_return(self):
    self.panel.show_event()
    self.panel.hide_event()
    close_future = self.panel.pending
    self.panel.show_event()
    close_future.set_result(None)
    self.panel._tick()
    self.assertIsNone(self.panel.status)
    self.assertEqual(self.panel.operation, 'snapshot')


if __name__ == '__main__':
  unittest.main()
