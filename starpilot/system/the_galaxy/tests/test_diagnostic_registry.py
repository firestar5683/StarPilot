from types import SimpleNamespace
from test_dashboard_stats import _load_server_module, FakeParams


def test_registry_sections_are_loggable_supported_and_read_only(monkeypatch):
  s = _load_server_module()
  monkeypatch.setattr(s, "params", FakeParams({"IsOnroad": False}))
  monkeypatch.setattr(s, "_TROUBLESHOOT_SECTION_DEFINITIONS", [])
  monkeypatch.setattr(s, "_get_param_type_info", lambda: (set(), {}))
  monkeypatch.setattr(s, "_get_default_param_values", lambda: {})
  monkeypatch.setattr(s, "_get_troubleshoot_learned_values", lambda: {})
  monkeypatch.setattr(s, "_get_layout_param_metadata", lambda: {"Parent": {"label": "Parent menu"}})
  monkeypatch.setattr(s, "_get_hardware_snapshot_items", lambda: [])
  monkeypatch.setattr(s, "_build_vehicle_fault_status", lambda: {"summary": "preserved"})
  monkeypatch.setattr(s, "_get_safety_snapshot_text", lambda: "stock safety")
  monkeypatch.setattr(s, "_get_fingerprint_snapshot_text", lambda: "fixture")
  monkeypatch.setattr(s.utilities, "get_current_lan_ip", lambda: "127.0.0.1")
  monkeypatch.setattr(s, "_safe_params_get", lambda *args, **kwargs: "")
  keys = ["NewSetting", "Secret", "RivianAngle", "TeslaWakeOnCAN", "ControllerActionSlots"]
  monkeypatch.setattr(s, "starpilot_default_params", [(key, None, None, None) for key in keys])
  monkeypatch.setattr(s, "_params_raw", SimpleNamespace(get_key_flag=lambda key: s.ParamKeyFlag.DONT_LOG if key == "Secret" else 0))
  monkeypatch.setattr(s, "_get_has_rivian_angle_harness", lambda: False)
  monkeypatch.setattr(s, "supports_tesla_can_wake", lambda params: False)
  monkeypatch.setattr(s, "load_settings_catalog", lambda: [{"name": "Category", "params": [
    {"key": "NewSetting", "parent_key": "Parent"}, {"key": "NewSetting"},
    {"key": "Secret"}, {"key": "Missing"}, {"key": "TeslaWakeOnCAN"},
    {"key": "RivianAngle", "requires_capability": "HasRivianAngleHarness"}]}])
  monkeypatch.setattr(s, "_build_troubleshoot_section_payload", lambda d, *args: {**d, "items": [{"key": k} for k in d["keys"]], "resettable": True})
  result = s._build_troubleshoot_payload()
  assert result["vehicleStatus"]["summary"] == "preserved"
  assert result["snapshot"][0]["value"] == "stock safety"
  sections = result["sections"]
  assert [k for section in sections for k in section["keys"]] == ["ControllerActionSlots", "NewSetting"]
  assert sections[1]["title"] == "Category › Parent menu"
  assert all(section["resettable"] is False for section in sections)
