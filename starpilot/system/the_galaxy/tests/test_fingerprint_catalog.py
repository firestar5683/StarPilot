from test_dashboard_stats import MODULE_DIR, _install_server_import_stubs


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

  assert {"value": "TESLA_MODEL_3", "label": "Tesla Model 3 (with HW3) 2019-23"} in tesla_models
  assert {"value": "TESLA_MODEL_3", "label": "Tesla Model 3 (with HW4) 2024-25"} in tesla_models
  assert {"value": "TESLA_MODEL_Y", "label": "Tesla Model Y (with HW3) 2020-23"} in tesla_models
  assert {"value": "TESLA_MODEL_X", "label": "Tesla Model X (with HW4) 2024"} in tesla_models
