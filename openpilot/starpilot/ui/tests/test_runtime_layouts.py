"""Exercise actual opt-in layout constructors with external owners isolated."""

import atexit
from contextlib import ExitStack
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from openpilot.common.params import Params


_param_dir = tempfile.TemporaryDirectory(prefix="starpilot-ui-layout-test-")
atexit.register(_param_dir.cleanup)
_original_params_init = Params.__init__
with patch.object(Params, "__init__", lambda self, d="": _original_params_init(self, _param_dir.name)):
  from openpilot.starpilot.ui import runtime_app


class TestOptInLayouts(unittest.TestCase):
  def _session(self):
    session = Mock()
    session.profile = runtime_app.Profile.COMPACT
    return session

  def test_large_constructor_routes_into_existing_layout_state_and_closes_camera(self):
    session = self._session()
    session.fonts.profile = runtime_app.Profile.LARGE
    camera = Mock()

    def parent_init(layout):
      from openpilot.selfdrive.ui.layouts.settings.settings import PanelType
      settings = Mock()
      settings._panels = {panel: NS(instance=Mock()) for panel in PanelType}
      settings._panels[PanelType.TOGGLES].instance._scroller._items = []
      layout._layouts = {runtime_app.MainState.HOME: Mock(), runtime_app.MainState.SETTINGS: settings,
                         runtime_app.MainState.ONROAD: camera}
      layout._current_mode = runtime_app.MainState.HOME

    with patch.object(runtime_app, "validate_runtime_fonts"), patch.object(runtime_app, "validate_runtime_assets"), \
         patch.object(runtime_app.MainLayout, "__init__", parent_init), \
         patch.object(runtime_app, "button_item"), \
         patch.object(runtime_app, "text_item"), \
         patch.object(runtime_app, "StarShellSession", return_value=session):
      layout = runtime_app.StarMainLayout()
      navigate = session.set_navigation.call_args.kwargs
      navigate["on_settings"]()
      self.assertEqual(layout._current_mode, runtime_app.MainState.SETTINGS)
      session.cancel.assert_called_once()
      with patch.object(runtime_app.ui_state, "is_body", True), \
           patch.object(runtime_app.MainLayout, "_render_main_content") as body_render:
        layout._set_current_layout(runtime_app.MainState.HOME)
        layout._render_main_content()
      body_render.assert_called_once()
      layout._rect = Mock()
      session.snapshot.return_value = NS(home=NS(paired=False))
      with patch.object(runtime_app.ui_state, "is_body", False), patch.object(layout.page, "render") as custom_render:
        layout._render_main_content()
      custom_render.assert_called_once_with(layout._rect)
      session.cancel.reset_mock()
      with patch.object(runtime_app.MainLayout, "_on_body_changed") as body_changed:
        layout._on_body_changed()
      session.cancel.assert_called_once()
      body_changed.assert_called_once()
      self.assertIs(layout._native_onroad, camera)
      layout.close()
    session.close.assert_called_once()
    camera.close.assert_called_once()

  def test_compact_constructor_replaces_scroller_pages_and_keeps_camera_owner(self):
    session = self._session()
    camera = Mock()
    scroller = NS(items=[Mock(), Mock(), Mock(), Mock()], set_scrolling_enabled=Mock())

    def parent_init(layout):
      layout._car_onroad_layout = camera
      layout._home_layout = Mock()
      layout._scroller = scroller

    with patch.object(runtime_app, "validate_runtime_fonts"), patch.object(runtime_app, "validate_runtime_assets"), \
         patch.object(runtime_app.MiciMainLayout, "__init__", parent_init), \
         patch.object(runtime_app.MiciMainLayout, "_on_body_changed"), \
         patch.object(runtime_app, "StarShellSession", return_value=session):
      layout = runtime_app.StarMiciMainLayout()
      self.assertIs(scroller.items[1], layout._home_layout)
      self.assertIs(scroller.items[2], layout._car_onroad_layout)
      self.assertIs(layout._native_onroad, camera)
      self.assertIsInstance(layout._settings_layout, runtime_app.StarCompactSettings)
      self.assertFalse(hasattr(layout._home_layout, "fallback"))
      navigate = session.set_navigation.call_args.kwargs
      with patch.object(runtime_app.gui_app, "push_widget") as push_widget:
        navigate["on_settings"]()
      push_widget.assert_called_once_with(layout._settings_layout)
      layout.close()
    session.close.assert_called_once()
    camera.close.assert_called_once()

  def test_compact_settings_are_lazy_and_pairing_keeps_native_owner(self):
    from openpilot.selfdrive.ui.mici.layouts import main

    for layout_type in (main.MiciMainLayout, runtime_app.StarMiciMainLayout):
      with self.subTest(layout=layout_type.__name__), ExitStack() as stack:
        def scroller_init(layout, **kwargs):
          layout._scroller = Mock()
          layout._scroller.items = [Mock(), Mock(), Mock(), Mock()]

        stack.enter_context(patch.object(main.Scroller, "__init__", scroller_init))
        for owner in ("MiciHomeLayout", "MiciOffroadAlerts", "AugmentedRoadView", "BodyLayout", "OnboardingWindow"):
          stack.enter_context(patch.object(main, owner))
        settings_factory = stack.enter_context(patch.object(main, "SettingsLayout"))
        stack.enter_context(patch.object(main.messaging, "PubMaster"))
        stack.enter_context(patch.object(main, "gui_app"))
        stack.enter_context(patch.object(main, "device"))
        stack.enter_context(patch.object(main, "ui_state"))
        stack.enter_context(patch.object(main.MiciMainLayout, "_on_body_changed"))
        stack.enter_context(patch.object(runtime_app, "validate_runtime_fonts"))
        stack.enter_context(patch.object(runtime_app, "validate_runtime_assets"))
        stack.enter_context(patch.object(runtime_app, "StarShellSession", return_value=self._session()))
        layout = layout_type()
        settings_factory.assert_not_called()
        pairing = layout._alerts_layout.set_pairing_callback.call_args.args[0]
        pairing()
        settings_factory.assert_called_once_with()
        native_settings = settings_factory.return_value
        native_settings.set_rect.assert_called_once()
        native_settings.show_pairing.assert_called_once_with()
        pairing()
        settings_factory.assert_called_once_with()
        if layout_type is main.MiciMainLayout:
          self.assertIs(layout._settings_layout, native_settings)
          with patch.object(main.gui_app, "push_widget") as push:
            layout._home_layout.set_callbacks.call_args.kwargs["on_settings"]()
          push.assert_called_once_with(native_settings)
        else:
          self.assertIsInstance(layout._settings_layout, runtime_app.StarCompactSettings)
          self.assertIsNot(layout._settings_layout, native_settings)

  def test_slc_publisher_reader_rejects_stale_transport_or_missing_started_evidence(self):
    from openpilot.starpilot.ui.tests.test_runtime_snapshot import NOW, BOOT_OFFSET_NS, ui_fake
    clocks = patch("openpilot.starpilot.ui.runtime_snapshot._clock_pair", return_value=(NOW, NOW + BOOT_OFFSET_NS, BOOT_OFFSET_NS))
    clocks.start()
    self.addCleanup(clocks.stop)
    ui = ui_fake()
    ui.CP = NS(openpilotLongitudinalControl=True, pcmCruise=False)
    ui.sm.messages["carState"].canTimeout = False
    ui.sm.messages["carState"].canValid = True
    ui.sm.messages["carControl"].longActive = True
    ui.sm.messages["selfdriveState"].enabled = True
    ui.sm.put("controlsState", NS(longControlState="pid"))
    session = runtime_app.StarShellSession.__new__(runtime_app.StarShellSession)
    session.adapter = runtime_app.RuntimeSnapshotAdapter(ui)
    self.assertIs(session._live_slc_message(NOW), ui.sm["slcState"])
    ui.sm.logMonoTime["slcState"] = NOW - 200_000_000
    self.assertIsNone(session._live_slc_message(NOW))
    ui.sm.logMonoTime["slcState"] = NOW
    ui.sm.valid["slcState"] = False
    self.assertIsNone(session._live_slc_message(NOW))
    ui.sm.valid["slcState"] = True
    ui.sm["pandaStates"][0].ignitionLine = False
    self.assertIsNone(session._live_slc_message(NOW))
    ui.sm["pandaStates"][0].ignitionLine = True
    ui.sm["carControl"].longActive = False
    self.assertIsNone(session._live_slc_message(NOW))
    ui.sm["carControl"].longActive = True
    ui.sm["carState"].canValid = False
    self.assertIsNone(session._live_slc_message(NOW))

  def test_slc_action_publisher_is_singleton_for_process(self):
    runtime_app._slc_action_publisher.cache_clear()
    try:
      with patch.object(runtime_app.messaging, "PubMaster") as owner:
        first = runtime_app._slc_action_publisher()
        self.assertIs(first, runtime_app._slc_action_publisher())
      owner.assert_called_once_with(["slcAction"])
    finally:
      runtime_app._slc_action_publisher.cache_clear()


if __name__ == "__main__":
  unittest.main()
