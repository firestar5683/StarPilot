from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SETTINGS_PATH = REPO_ROOT / "starpilot/system/the_galaxy/assets/components/settings.js"
ROUTER_PATH = REPO_ROOT / "starpilot/system/the_galaxy/assets/components/router.js"
INDEX_PATH = REPO_ROOT / "starpilot/system/the_galaxy/templates/index.html"
BLUETOOTH_PATH = REPO_ROOT / "starpilot/system/the_galaxy/assets/components/tools/bluetooth.js"
CONTROLLERS_PATH = REPO_ROOT / "starpilot/system/the_galaxy/assets/components/tools/wheel_controls.js"
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
  assert "/assets/components/router.js?v=router-public-path-6" in index
  assert "/assets/components/tools/bluetooth.js?v=bluetooth-live-15" in router
  assert "/assets/components/tools/bluetooth.css?v=bluetooth-6" in index


def test_public_galaxy_bootstrap_keeps_the_device_path_for_module_imports():
  index = INDEX_PATH.read_text(encoding="utf-8")

  assert 'window.location.hostname === "galaxy.firestar.link"' in index
  assert '/^[A-Za-z0-9]{16}$/.test(firstPathSegment)' in index
  assert 'window.__theGalaxyBasePath = galaxyBasePath' in index
  assert 'galaxyImportMap.type = "importmap"' in index
  assert 'JSON.stringify({ imports: { "/assets/": `${galaxyBasePath}/assets/` } })' in index
  assert '`${window.__theGalaxyBasePath}/assets/components/router.js?v=router-public-path-6`' in index


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
  assert "state.enabled && !state.companionDevices.length" in source
  assert "state.operationError || state.statusError" in source
  assert "<h3>Phone connection</h3>" in source
  assert "Open the iPhone app that will connect to StarPilot" in source
  assert "Tap Connect and choose StarPilot" in source
  assert "no confirmation slider is shown" in source
  assert "isCompanionDevice(device) && !device.connected" in source
  assert "Reconnect from phone" in source


def test_bluetooth_device_list_rerenders_when_state_changes():
  source = BLUETOOTH_PATH.read_text(encoding="utf-8")

  assert "renderDeviceSection(title, icon, devices, emptyText" in source
  assert 'renderDeviceSection("My Devices", "bi-check2-circle", knownDevices()' in source
  assert 'renderDeviceSection("Available Devices", "bi-radar", availableDevices()' in source
  assert "state.deviceSignature !== deviceSignature" in source
  assert "state.revision++" in source


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
  assert "Nothing is compiled on the comma" in source
  assert "run every camera frame on Chestnut's AMD GPU" in source
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
  assert 'model_laboratory.js?v=model-lab-5' in ROUTER_PATH.read_text(encoding="utf-8")
  assert 'model_laboratory.css?v=model-lab-4' in INDEX_PATH.read_text(encoding="utf-8")
