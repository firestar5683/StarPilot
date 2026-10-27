from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

import pytest

from openpilot.starpilot.ui.onroad_customization import default_document
from openpilot.starpilot.ui.onroad_jetlink_layer import NativeJetlinkLayer
from openpilot.starpilot.ui.onroad_jetlink import JetlinkStatusWidget


def test_native_jetlink_polls_only_while_its_widget_is_showing_onroad():
  with patch('openpilot.starpilot.ui.onroad_jetlink_layer.gui_app') as app, \
       patch('openpilot.starpilot.ui.onroad_jetlink_layer.JetlinkStatusFeed') as feed:
    widget, ui = Mock(), NS(started=True)
    layer = NativeJetlinkLayer(widget, ui)
    state = NS(customization=default_document())
    app.add_render_prepare.assert_called_once_with(layer.prepare, layer.close)
    layer.render(state)
    layer.prepare()
    widget.render.assert_not_called()  # Off by default.
    feed.return_value.set_enabled.assert_called_with(False)
    state.customization['layouts']['large']['jetlink_status']['enabled'] = True
    layer.render(state)
    assert widget.status is feed.return_value.snapshot.return_value
    widget.render.assert_called_once_with(state)
    layer.prepare()
    feed.return_value.set_enabled.assert_called_with(True)
    layer.prepare()  # No render request: the page is hidden.
    feed.return_value.set_enabled.assert_called_with(False)
    layer.render(state)
    ui.started = False
    layer.prepare()
    feed.return_value.set_enabled.assert_called_with(False)
    layer.close()
    app.remove_render_prepare.assert_called_once_with(layer.prepare)
    feed.return_value.close.assert_called_once()


def test_opted_in_widget_shows_off_and_hides_under_alerts():
  fonts = Mock()
  fonts.measure.return_value = NS(width=100)
  widget = JetlinkStatusWidget(fonts)
  state = NS(customization=default_document(), alert=NS(size='none'))
  state.customization['layouts']['large']['jetlink_status']['enabled'] = True
  with patch('openpilot.starpilot.ui.onroad_jetlink.rl.draw_rectangle_rounded'), \
       patch('openpilot.starpilot.ui.onroad_jetlink.rl.draw_circle_v'):
    widget.render(state)
    assert [call.args[0] for call in fonts.draw.call_args_list] == ['JetLink', 'JetLink off • Local model']
    fonts.draw.reset_mock()
    state.alert.size = 'full'
    widget.render(state)
    fonts.draw.assert_not_called()



def test_widget_uses_preparation_detail_and_ready_overrides_progress():
  from openpilot.starpilot.models.jetlink_status import JetlinkStatus
  from openpilot.starpilot.ui.onroad_jetlink import status_lines
  assert status_lines(JetlinkStatus(state='detected')) == ('JetLink', 'Device detected • waiting for USB')
  assert status_lines(JetlinkStatus(state='connecting')) == ('JetLink', 'Device connected • waiting for app')
  assert status_lines(JetlinkStatus(state='preparing', stage='warm')) == ('JetLink', 'Warming up model • device connected')
  assert status_lines(JetlinkStatus(state='preparing', stage='upload', percent=42)) == ('JetLink', 'Sending model • 42% transferred')
  assert status_lines(JetlinkStatus(state='waiting', stage='warm')) == ('JetLink', 'Ready to switch • waiting to disengage')
  assert status_lines(JetlinkStatus(state='reconnecting')) == ('JetLink', 'Reconnecting • restoring connection')
  assert status_lines(JetlinkStatus(state='reconnecting', stage='reconnect_behind')) == ('JetLink', 'Reconnecting • device too slow')
  assert status_lines(JetlinkStatus(state='reconnecting', stage='reconnect_cable')) == (
    'JetLink', 'Reconnecting • link keeps dropping, check cable')
  assert status_lines(JetlinkStatus(state='active', stage='warm')) == ('JetLink', 'Remote model active')


@pytest.mark.parametrize('projected', [False, True], ids=['native-3x', 'android-auto'])
def test_preparation_renders_in_native_and_projected_layout(projected):
  from openpilot.starpilot.models.jetlink_status import JetlinkStatus
  from openpilot.starpilot.system.android_auto.projection_layout import default_layout_for_viewport, projection_customization
  document = default_document()
  if projected:
    layout = default_layout_for_viewport((2880, 1080))
    layout['widgets']['jetlink_status'].update(enabled=True, x=700, y=500)
    document = projection_customization(layout, document)
  else:
    document['layouts']['large']['jetlink_status']['enabled'] = True
  fonts = Mock()
  fonts.measure.return_value = NS(width=100)
  widget = JetlinkStatusWidget(fonts)
  widget.status = JetlinkStatus(state='preparing', stage='warm')
  with patch('openpilot.starpilot.ui.onroad_jetlink.rl.draw_rectangle_rounded') as card, \
       patch('openpilot.starpilot.ui.onroad_jetlink.rl.draw_circle_v'):
    widget.render(NS(customization=document, alert=NS(size='none')))
  assert [call.args[0] for call in fonts.draw.call_args_list] == ['JetLink', 'Warming up model • device connected']
  placement = document['layouts']['large']['jetlink_status']
  assert card.call_args.args[0].x == placement['x']
  assert card.call_args.args[0].y == placement['y']


@pytest.mark.parametrize('projected', [False, True], ids=['native-3x', 'android-auto'])
@pytest.mark.parametrize('hide', [False, True])
@pytest.mark.parametrize('status', ['off', 'disconnected', 'detected', 'connecting', 'preparing', 'waiting', 'active', 'reconnecting', 'failed', 'unavailable'])
def test_hide_disconnected_only_hides_idle_states(projected, hide, status):
  from openpilot.starpilot.models.jetlink_status import JetlinkStatus
  from openpilot.starpilot.system.android_auto.projection_layout import default_layout_for_viewport, projection_customization
  document = default_document()
  if projected:
    document = projection_customization(default_layout_for_viewport((2880, 1080)), document)
  document['layouts']['large']['jetlink_status'].update(enabled=True, hideDisconnected=hide)
  fonts = Mock()
  fonts.measure.return_value = NS(width=100)
  widget = JetlinkStatusWidget(fonts)
  widget.status = JetlinkStatus(state=status)
  with patch('openpilot.starpilot.ui.onroad_jetlink.rl.draw_rectangle_rounded') as card, \
       patch('openpilot.starpilot.ui.onroad_jetlink.rl.draw_circle_v'):
    widget.render(NS(customization=document, alert=NS(size='none')))
  assert card.called == (not hide or status not in ('off', 'disconnected'))


def test_jetlink_hide_disconnected_round_trip_and_migration():
  from openpilot.starpilot.ui.onroad_customization import validate_document
  document = default_document()
  placed = document['layouts']['large']['jetlink_status']
  assert placed['hideDisconnected'] is False
  placed['hideDisconnected'] = True
  assert validate_document(document)['layouts']['large']['jetlink_status']['hideDisconnected'] is True
  del placed['hideDisconnected']
  assert validate_document(document)['layouts']['large']['jetlink_status']['hideDisconnected'] is False
  for bad in (None, 1, 'true'):
    placed['hideDisconnected'] = bad
    with pytest.raises(ValueError):
      validate_document(document)


def test_projected_jetlink_hide_setting_round_trip_and_migration():
  from openpilot.starpilot.system.android_auto.projection_layout import default_layout_for_viewport, validate_layout_for_viewport, projection_customization
  viewport = (2880, 1080)
  document = default_layout_for_viewport(viewport)
  placement = document['widgets']['jetlink_status']
  assert placement['hideDisconnected'] is False
  placement['hideDisconnected'] = True
  validated = validate_layout_for_viewport(document, viewport)
  assert projection_customization(validated, default_document())['layouts']['large']['jetlink_status']['hideDisconnected'] is True
  del placement['hideDisconnected']
  assert validate_layout_for_viewport(document, viewport)['widgets']['jetlink_status']['hideDisconnected'] is False
  for bad in (None, 1, 'true'):
    placement['hideDisconnected'] = bad
    with pytest.raises(ValueError):
      validate_layout_for_viewport(document, viewport)
