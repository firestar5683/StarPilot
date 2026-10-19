from test_dashboard_stats import MODULE_DIR, _install_server_import_stubs
from test_navigation_params import WritableFakeParams, _params_client, the_galaxy as api_server


def _load_server_module():
  import importlib.util

  _install_server_import_stubs()
  spec = importlib.util.spec_from_file_location("fingerprint_catalog_server", MODULE_DIR / "the_galaxy.py")
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


the_galaxy = _load_server_module()


def test_galaxy_lists_tesla_hardware_specific_docs_for_manual_fingerprinting():
  tesla_models = the_galaxy._extract_fingerprint_models_for_make("tesla")

  assert {"value": "TESLA_MODEL_S_PREAP", "label": "Tesla Model S (Pre-AP) 2012-14"} in tesla_models
  assert {"value": "TESLA_MODEL_S_HW1", "label": "Tesla Model S (with HW1) 2014-16"} in tesla_models
  assert {"value": "TESLA_MODEL_S_PREAP", "label": "Tesla Model S (with HW1) 2014-16"} not in tesla_models
  assert {"value": "TESLA_MODEL_3", "label": "Tesla Model 3 (with HW3) 2019-23"} in tesla_models
  assert {"value": "TESLA_MODEL_3", "label": "Tesla Model 3 (with HW4) 2024-26"} in tesla_models
  assert {"value": "TESLA_MODEL_Y", "label": "Tesla Model Y (with HW3) 2020-23"} in tesla_models
  assert {"value": "TESLA_MODEL_X", "label": "Tesla Model X (with HW4) 2024"} in tesla_models

  catalog = the_galaxy._get_fingerprint_catalog()
  assert catalog["label_to_model"]["Tesla Model S (with HW1) 2014-16"] == "TESLA_MODEL_S_HW1"


def test_galaxy_does_not_assign_a_regional_label_to_ambiguous_ev6_fingerprint():
  kia_models = the_galaxy._extract_fingerprint_models_for_make("kia")
  assert {"value": "KIA_EV6", "label": "Kia EV6 (Southeast Asia only) 2022-24"} in kia_models
  assert {"value": "KIA_EV6", "label": "Kia EV6 (with HDA II) 2022-24"} in kia_models

  catalog = the_galaxy._get_fingerprint_catalog()
  assert catalog["model_to_label"]["KIA_EV6"] is None


def test_galaxy_lists_2026_k4_under_existing_non_hda2_platform():
  kia_models = the_galaxy._extract_fingerprint_models_for_make("kia")
  assert {"value": "KIA_K4_2025", "label": "Kia K4 (without HDA II) 2025"} in kia_models
  assert {"value": "KIA_K4_2025", "label": "Kia K4 (without HDA II) 2026"} in kia_models
  assert {"value": "KIA_K4_2025", "label": "Kia K4 (with HDA II) 2025"} in kia_models
  assert {"value": "KIA_K4_2025", "label": "Kia K4 (with HDA II) 2025-26"} not in kia_models


def test_manual_2026_k4_selection_keeps_the_shared_platform(monkeypatch):
  client, params = _params_client(monkeypatch, {}, "pc")
  monkeypatch.setattr(api_server, "_get_param_type_info", lambda: ({"CarModel"}, {"CarModel": str}))
  monkeypatch.setattr(api_server, "update_starpilot_toggles", lambda: None)

  label = "Kia K4 (without HDA II) 2026"
  options = client.get("/api/fingerprints/models?make=Kia").get_json()
  assert {"value": "KIA_K4_2025", "label": label} in options
  response = client.put("/api/params", json={"key": "CarModel", "value": "KIA_K4_2025", "label": label})
  assert response.status_code == 200
  assert params.values["CarModel"] == "KIA_K4_2025"
  assert params.values["CarModelName"] == label


def test_manual_fingerprint_api_keeps_the_saved_value_and_label_consistent(monkeypatch):
  client, params = _params_client(monkeypatch, {}, "pc")
  monkeypatch.setattr(api_server, "_get_param_type_info", lambda: ({"CarModel"}, {"CarModel": str}))
  monkeypatch.setattr(api_server, "update_starpilot_toggles", lambda: None)

  hw1_label = "Tesla Model S (with HW1) 2014-16"
  options = client.get("/api/fingerprints/models?make=Tesla").get_json()
  assert {"value": "TESLA_MODEL_S_HW1", "label": hw1_label} in options
  response = client.put("/api/params", json={"key": "CarModel", "value": "TESLA_MODEL_S_HW1", "label": hw1_label})
  assert response.status_code == 200
  assert params.values["CarModel"] == "TESLA_MODEL_S_HW1"
  assert params.values["CarModelName"] == hw1_label

  response = client.put("/api/params", json={"key": "CarModel", "value": "TESLA_MODEL_S_PREAP", "label": hw1_label})
  assert response.status_code == 400
  assert params.values["CarModel"] == "TESLA_MODEL_S_HW1"
  assert params.values["CarModelName"] == hw1_label

  preap_label = "Tesla Model S (Pre-AP) 2012-14"
  response = client.put("/api/params", json={"key": "CarModel", "value": "TESLA_MODEL_S_PREAP", "label": preap_label})
  assert response.status_code == 200
  assert params.values["CarModel"] == "TESLA_MODEL_S_PREAP"
  assert params.values["CarModelName"] == preap_label

  response = client.put("/api/params", json={"key": "CarModel", "value": "KIA_EV6"})
  assert response.status_code == 200
  assert params.values["CarModel"] == "KIA_EV6"
  assert "CarModelName" not in params.values

  hda_label = "Kia EV6 (with HDA II) 2022-24"
  response = client.put("/api/params", json={"key": "CarModel", "value": "KIA_EV6", "label": hda_label})
  assert response.status_code == 200
  assert params.values["CarModelName"] == hda_label


def test_fingerprint_diagnostic_flags_a_stale_label_value_mismatch(monkeypatch):
  monkeypatch.setattr(the_galaxy, "params", WritableFakeParams({
    "CarModel": "TESLA_MODEL_S_PREAP",
    "CarModelName": "Tesla Model S (with HW1) 2014-16",
  }))
  text = the_galaxy._get_fingerprint_snapshot_text()
  assert "Mismatch" in text
  assert "TESLA_MODEL_S_PREAP" in text
  assert "reselect" in text.lower()
