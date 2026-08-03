from openpilot.selfdrive.ui.lib.fingerprint_catalog import _extract_fingerprint_models_for_make, get_fingerprint_catalog


def test_tesla_hardware_specific_docs_are_available_for_manual_fingerprinting():
  tesla_models = _extract_fingerprint_models_for_make("tesla")

  assert ("TESLA_MODEL_3", "Tesla Model 3 (with HW3) 2019-23", "Tesla") in tesla_models
  assert ("TESLA_MODEL_3", "Tesla Model 3 (with HW4) 2024-25", "Tesla") in tesla_models
  assert ("TESLA_MODEL_Y", "Tesla Model Y (with HW3) 2020-23", "Tesla") in tesla_models
  assert ("TESLA_MODEL_X", "Tesla Model X (with HW4) 2024", "Tesla") in tesla_models


def test_tesla_model_3_hardware_variants_remain_distinct_menu_options():
  _, models_by_make, _, _ = get_fingerprint_catalog()
  model_3_options = [option for option in models_by_make["Tesla"] if option.value == "TESLA_MODEL_3"]

  assert [option.label for option in model_3_options] == [
    "Tesla Model 3 (with HW3) 2019-23",
    "Tesla Model 3 (with HW4) 2024-25",
  ]
