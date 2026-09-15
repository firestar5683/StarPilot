from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SETTINGS_PATH = REPO_ROOT / "starpilot/system/the_galaxy/assets/components/settings.js"
ROUTER_PATH = REPO_ROOT / "starpilot/system/the_galaxy/assets/components/router.js"
INDEX_PATH = REPO_ROOT / "starpilot/system/the_galaxy/templates/index.html"
BLUETOOTH_PATH = REPO_ROOT / "starpilot/system/the_galaxy/assets/components/tools/bluetooth.js"
CONTROLLERS_PATH = REPO_ROOT / "starpilot/system/the_galaxy/assets/components/tools/wheel_controls.js"
MOBILE_CONTROLLERS_PATH = REPO_ROOT / "starpilot/system/the_galaxy/assets/mobile/js/components/WheelControls.js"
SIDEBAR_PATH = REPO_ROOT / "starpilot/system/the_galaxy/assets/components/sidebar.js"
MODEL_LAB_PATH = REPO_ROOT / "starpilot/system/the_galaxy/assets/components/tools/model_laboratory.js"


def test_settings_does_not_create_a_second_router_module():
  source = SETTINGS_PATH.read_text(encoding="utf-8")

  assert "/assets/components/router.js" not in source
  assert "window.__theGalaxyNavigate" in source


def test_router_and_settings_cache_bust_is_consistent():
  router = ROUTER_PATH.read_text(encoding="utf-8")
  index = INDEX_PATH.read_text(encoding="utf-8")

  assert "/assets/components/settings.js?v=router-cycle-fix-5" in router
  assert "/assets/components/router.js?v=router-cycle-fix-8" in index
  assert "/assets/components/sidebar.js?v=sidebar-pin-2" in router
  assert "/assets/components/main.css?v=sidebar-pin-2" in index
  assert "/assets/components/sidebar.css?v=sidebar-pin-2" in index


def test_bluetooth_actions_use_reactive_disabled_bindings():
  source = BLUETOOTH_PATH.read_text(encoding="utf-8")

  assert 'disabled="${pairingDisabled}"' not in source
  assert 'disabled="${disabled}"' not in source
  assert 'disabled="${() => !state.offroad || !!state.busy}"' in source
  assert "bluetoothAddress" not in source
  assert 'address: audioSelected() ? "" : device.address' in source
  assert 'audioSelected() ? "Stop Using for Audio" : "Use for Audio"' in source
  assert 'request("test_audio", { address: device.address })' in source
  assert "startAudioTestCountdown" in source
  assert "The test sound is sent at NOW" in source
  assert 'renderDeviceSection("My Devices"' in source
  assert 'renderDeviceSection("Available Devices"' in source
  assert "bluetoothForgetButton" in source
  assert "bi-trash3" in source
  assert "state.pairingAddress" in source
  assert "state.busy !== \"power\"" in source
  assert "Turning Bluetooth" in source
  assert "!device.paired" in source
  assert 'galaxyPath("/bluetooth")' in source
  assert 'window.location.pathname === "/bluetooth"' not in source
  assert "schedulePoll(250)" in source
  assert "while (refreshRequested)" in source
  assert 'cache: "no-store"' in source
  assert "const ACTIVE_POLL_INTERVAL_MS = 250" in source
  assert "document.visibilityState !== \"hidden\"" in source
  assert "window.addEventListener(\"pageshow\", refresh)" in source
  assert 'state.revision)' in source
  assert "const revisionAttribute" in source
  assert 'data-revision="${revision}"' in source
  assert 'bluetooth-live-15' in ROUTER_PATH.read_text(encoding="utf-8")


def test_controller_test_mode_has_explicit_start_and_stop():
  source = CONTROLLERS_PATH.read_text(encoding="utf-8")

  assert 'state.testing ? "test-stop" : "test"' in source
  assert 'state.lastTested.mapped ? "Successful" : "Not mapped"' in source
  assert "Controller inputs are temporarily consumed" in source


def test_controller_joystick_mode_requires_explicit_device_selection():
  source = CONTROLLERS_PATH.read_text(encoding="utf-8")

  assert "Favorite buttons are the default" in source
  assert "Enable for Joystick Mode" in source
  assert 'request("joystick", { device_id: device.device_id, enabled: !selected() })' in source


def test_controller_offroad_disconnect_is_opt_in():
  source = CONTROLLERS_PATH.read_text(encoding="utf-8")
  mobile_source = MOBILE_CONTROLLERS_PATH.read_text(encoding="utf-8")

  for frontend in (source, mobile_source):
    assert "Disconnect controllers when offroad" in frontend
    assert "After two minutes offroad" in frontend
    assert "offroad-disconnect" in frontend


def test_controller_page_has_ten_controller_only_action_slots():
  source = CONTROLLERS_PATH.read_text(encoding="utf-8")

  assert "Controller-only Actions" in source
  assert "These never appear as on-screen Favorites" in source
  assert 'request("action", { slot: index, key, value })' in source
  assert "const targetIndex = 3 + index" in source
  assert "state.controllerSlots.map(controllerSlotCard)" in source
  assert "Set speed (${() => state.speedUnit})" in source
  assert "Galaxy → Sentry Mode" in source


def test_bluetooth_and_controllers_sidebar_order():
  source = SIDEBAR_PATH.read_text(encoding="utf-8")

  toggles = source.index('{ name: "Toggles"')
  bluetooth = source.index('{ name: "Bluetooth"')
  sentry = source.index('{ name: "Sentry Mode"')
  controllers = source.index('{ name: "Controllers"')
  assert toggles < bluetooth < sentry < controllers


def test_sidebar_pin_state_and_responsive_drawer_are_wired():
  sidebar = SIDEBAR_PATH.read_text(encoding="utf-8")
  template = INDEX_PATH.read_text(encoding="utf-8")
  sidebar_css = (REPO_ROOT / "starpilot/system/the_galaxy/assets/components/sidebar.css").read_text(encoding="utf-8")
  main_css = (REPO_ROOT / "starpilot/system/the_galaxy/assets/components/main.css").read_text(encoding="utf-8")
  navigation_css = (REPO_ROOT / "starpilot/system/the_galaxy/assets/components/navigation/navigation_destination.css").read_text(encoding="utf-8")

  assert 'window.localStorage?.getItem(SIDEBAR_PINNED_KEY)' in sidebar
  assert 'stored === "true"' in sidebar and 'defaultSidebarPinned' in sidebar
  assert "try {" in sidebar
  assert 'menuButton.dataset.boundClick !== "1"' in sidebar
  assert 'class="sidebar-pin-button"' in sidebar
  assert '<button id="menu_button"' in template
  assert 'aria-controls="sidebar"' in template
  assert "@media only screen and (max-width: 767px)" in sidebar_css
  assert "@media only screen and (min-width: 768px)" in sidebar_css
  assert "@media only screen and (min-width: var(--breakpoint-md))" not in sidebar_css
  assert "html.galaxy-sidebar-pinned .content" in main_css
  assert "html.galaxy-sidebar-pinned .map-wrapper" in navigation_css

def test_model_laboratory_is_wired_into_classic_and_mobile_navigation():
  router = ROUTER_PATH.read_text(encoding="utf-8")
  sidebar = SIDEBAR_PATH.read_text(encoding="utf-8")
  template = INDEX_PATH.read_text(encoding="utf-8")
  mobile_tools = (REPO_ROOT / "starpilot/system/the_galaxy/assets/mobile/js/views/Tools.js").read_text(encoding="utf-8")
  mobile_embed = (REPO_ROOT / "starpilot/system/the_galaxy/assets/mobile/js/views/ToolEmbed.js").read_text(encoding="utf-8")

  assert MODEL_LAB_PATH.is_file()
  assert 'createRoute("model_laboratory", "/model_laboratory", ModelLaboratory)' in router
  assert '{ name: "Model Laboratory", link: "/model_laboratory"' in sidebar
  assert "/assets/components/tools/model_laboratory.css" in template
  assert '{ name: "Model Laboratory", link: "/model_laboratory"' in mobile_tools
  assert '"/model_laboratory": "Model Laboratory"' in mobile_embed


def test_model_laboratory_frontend_exposes_guards_and_role_copy():
  source = MODEL_LAB_PATH.read_text(encoding="utf-8")
  assert 'if (!state.chestnutReady)' in source
  assert 'if (state.isOnroad)' in source
  assert "model.modelLabArtifactInstalled" in source
  assert "Download eGPU-compatible small models" in source
  assert "Choose from downloaded eGPU variant combinations below" in source
  assert "Download eGPU variant" in source
  assert "Delete eGPU variant" in source
  assert "Nothing is compiled on the comma" not in source
  assert "availableModels().filter(model => model.modelLabArtifactInstalled)" in source
  assert source.index("<h3>Available models</h3>") < source.index("<h3>Compose a pair</h3>")
  assert 'lateral.value === longitudinal.value' in source
  assert 'lateral.version !== longitudinal.version' not in source
  assert 'class="ml-chip ${' not in source
  assert 'class="ml-state ${() =>' not in source
  assert 'class="${() => `ml-chip ${' in source
  assert 'class="${() => `ml-state ${' in source
  assert "Path shape, curvature, lane geometry" in source
  assert "Speed, acceleration, stopping, leads" in source
  assert "Chestnut experiment" not in source
  assert "Manifest shortcomings" not in source
  assert "Opportunities" not in source
  assert "let selectionDirty = false" in source
  assert "lateralModel: selectionDirty" in source
  assert "longitudinalModel: selectionDirty" in source
  assert source.count("selectionDirty = true") == 2
  assert "selectionDirty = false\n    applyPayload(payload)" in source
  assert 'model_laboratory.js?v=model-lab-6' in ROUTER_PATH.read_text(encoding="utf-8")
  assert 'model_laboratory.css?v=model-lab-5' in INDEX_PATH.read_text(encoding="utf-8")
