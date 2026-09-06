import json
import subprocess
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "assets/components/tools/personality_profiles.mjs"
DEVICE_SETTINGS_PATH = MODULE_PATH.with_name("device_settings.js")
DEVICE_SETTINGS_CSS_PATH = MODULE_PATH.with_name("device_settings.css")
DEVICE_SETTINGS_LAYOUT_PATH = MODULE_PATH.parents[5] / "common/assets/device_settings_layout.json"
SNACKBAR_PATH = MODULE_PATH.parents[2] / "js/snackbar.js"


def _run_node(script):
  harness = f"""
    import * as profiles from {json.dumps(MODULE_PATH.as_uri())};
    const {{ formatProfileSpeed, profileSpeedUnit, valueFromPointer }} = profiles;
    {script}
  """
  result = subprocess.run(["node", "--input-type=module"], input=harness, capture_output=True, text=True, timeout=30)
  assert result.returncode == 0, result.stderr
  return json.loads(result.stdout)


def test_graph_speed_labels_follow_the_selected_unit_system():
  result = _run_node("""
    console.log(JSON.stringify([
      formatProfileSpeed(10, false),
      formatProfileSpeed(10, true),
      profileSpeedUnit(false),
      profileSpeedUnit(true),
    ]));
  """)
  assert result == ["10", "16.1", "mph", "km/h"]


def test_graph_pointer_values_are_clamped_and_snapped():
  result = _run_node("""
    console.log(JSON.stringify([
      valueFromPointer(100, { top: 100, height: 200 }, 0.5, 2.0, 0.05),
      valueFromPointer(200, { top: 100, height: 200 }, 0.5, 2.0, 0.05),
      valueFromPointer(350, { top: 100, height: 200 }, 0.5, 2.0, 0.05),
    ]));
  """)
  assert result == [2.0, 1.25, 0.5]


def test_saved_high_curve_points_remain_inside_the_graph_without_widening_authoring_limits():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  geometry_function = "function graphGeometry" + source.split("function graphGeometry", 1)[1].split("\n}\n", 1)[0] + "\n}"
  result = _run_node("""
    const state = { personalityMeta: { bounds: { acceleration: [0, 3.5] },
      speedBreakpointsMph: { acceleration: [0,10,20,30,40,50,60,70,80,90] } } };
  """ + geometry_function + """
    const curve = [6, 4, 3.51, 3.5, 3, 2, 1, 0.8, 0.4, 0];
    const geometry = graphGeometry("acceleration", curve);
    console.log(JSON.stringify({
      visible: curve.every(value => geometry.y(value) >= geometry.top && geometry.y(value) <= geometry.height - geometry.bottom),
      authoringBounds: state.personalityMeta.bounds.acceleration,
      displayBounds: geometry.bounds,
      curve,
    }));
  """)
  assert result["visible"] is True
  assert result["displayBounds"] == [0, 6]
  assert result["authoringBounds"] == [0, 3.5]
  assert result["curve"] == [6, 4, 3.51, 3.5, 3, 2, 1, 0.8, 0.4, 0]


def test_saved_high_curve_plot_does_not_raise_number_input_limits():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  functions = "\n".join(
    "function " + name + source.split("function " + name, 1)[1].split("\n}\n", 1)[0] + "\n}"
    for name in ("graphGeometry", "renderPersonalityCurve")
  )
  result = _run_node("""
    const state = { values: {}, personalityCurveErrors: {}, personalityMeta: {
      bounds: { acceleration: [0, 3.5] }, speedBreakpointsMph: { acceleration: [0,10,20,30,40,50,60,70,80,90] }
    } };
    const PERSONALITY_CATEGORY_DEFINITIONS = { acceleration: {label: "Acceleration", valueUnit: "m/s²", step: 0.01} };
    const personalityUpdateKey = (profile, category) => `${profile}-${category}`;
    const requestAnimationFrame = () => {};
    const html = (parts, ...values) => parts.reduce((text, part, i) => text + part + (values[i] ?? ""), "");
  """ + functions + """
    const rendered = renderPersonalityCurve({id: "aggressive", label: "Aggressive"}, "acceleration", {preset:"custom",curve:[6,4,3.51,3,2,1,1,1,1,1]});
    console.log(JSON.stringify({maxima:[...rendered.matchAll(/max="([^"]+)"/g)].map(match=>match[1]), warning:rendered.includes("Saved values above") }));
  """)
  assert result["maxima"] == ["3.5"] * 10
  assert result["warning"] is True


def test_drag_on_expanded_saved_curve_uses_plot_scale_but_caps_only_edited_point():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  functions = "\n".join(
    "function " + name + source.split("function " + name, 1)[1].split("\n}\n", 1)[0] + "\n}"
    for name in ("graphGeometry", "beginPersonalityCurveDrag")
  )
  result = _run_node("""
    const state = { personalityUpdating:{}, personalityProfiles:{aggressive:{acceleration:{preset:"custom",curve:[6,4,1,1,1,1,1,1,1,1]}}},
      personalityMeta:{bounds:{acceleration:[0,3.5]},speedBreakpointsMph:{acceleration:[0,10,20,30,40,50,60,70,80,90]}} };
    const PERSONALITY_CATEGORY_DEFINITIONS = { acceleration:{label:"Acceleration",step:0.01} };
    const personalityUpdateKey = (p,c) => `${p}-${c}`;
    const updates=[]; const saves=[];
    const updateDraggedCurveVisual = (canvas,p,c,curve,geometry) => updates.push({curve:[...curve],bounds:geometry?.bounds});
    const restorePersonalityCurveVisual = () => {};
    const savePersonalityCategory = async (p,c,preset,curve) => {saves.push([...curve]);return true;};
    class HTMLCanvasElement {
      constructor(){this.listeners={};this.dataset={};}
      getBoundingClientRect(){return {left:0,top:0,width:660,height:240};}
      setPointerCapture(){} hasPointerCapture(){return false;}
      addEventListener(name,fn){this.listeners[name]=fn;}
      removeEventListener(name){delete this.listeners[name];}
    }
  """ + functions + """
    const canvas=new HTMLCanvasElement();
    beginPersonalityCurveDrag({currentTarget:canvas,clientX:46,clientY:111,pointerId:1,preventDefault(){}},"aggressive","acceleration");
    canvas.listeners.pointermove({clientY:18});
    await canvas.listeners.pointerup({pointerId:1});
    console.log(JSON.stringify({updates,saves,original:state.personalityProfiles.aggressive.acceleration.curve}));
  """)
  assert result["updates"][0]["curve"] == [3, 4] + [1] * 8
  assert result["updates"][1]["curve"] == [3.5, 4] + [1] * 8
  assert all(update["bounds"] == [0, 6] for update in result["updates"])
  assert result["saves"] == [[3.5, 4] + [1] * 8]
  assert result["original"] == [6, 4] + [1] * 8


def test_rendered_editor_has_parked_locks_units_and_all_three_profile_categories():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  assert 'disabled="${() => !!state.values.IsOnroad' in source
  assert 'aria-disabled="${() => !!state.values.IsOnroad || !!state.personalityMigrationRequired}"' in source
  assert "profileSpeedUnit" in source
  assert "m/s²" in source
  for category in ("acceleration", "braking", "following"):
    assert f'renderPersonalityCategoryField(profile, "{category}"' in source
  assert 'following: { label: "Following"' in source
  assert 'param.key === "CustomPersonalities" && state.expanded[param.key]' in source
  assert 'param.key === "CustomPersonalities" && isParamEnabledForChildren(param)' not in source
  assert '<button type="button" class="ds-manage-btn"' in source


def test_acceleration_and_braking_presets_render_from_weakest_to_strongest():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  assert 'acceleration: ["eco", "standard", "sport", "sport_plus", "custom"]' in source
  assert 'braking: ["eco", "standard", "sport", "custom"]' in source


def test_profile_master_and_advanced_controls_declare_parked_only_metadata():
  layout = json.loads(DEVICE_SETTINGS_LAYOUT_PATH.read_text(encoding="utf-8"))
  params = {param["key"]: param for section in layout for param in section.get("params", [])}
  keys = {
    "CustomPersonalities",
    *{f"{profile}PersonalityProfile" for profile in ("Traffic", "Aggressive", "Standard", "Relaxed")},
    "TrafficFollow",
    "AggressiveFollow",
    "AggressiveFollowHigh",
    "StandardFollow",
    "StandardFollowHigh",
    "RelaxedFollow",
    "RelaxedFollowHigh",
    *{
      f"{profile}{suffix}"
      for profile in ("Traffic", "Aggressive", "Standard", "Relaxed")
      for suffix in ("JerkAcceleration", "JerkDeceleration", "JerkDanger", "JerkSpeedDecrease", "JerkSpeed")
    },
  }
  assert all(params[key].get("requires_offroad") is True for key in keys)


def test_profile_errors_are_escaped_before_the_legacy_html_snackbar_sink():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  helper = source.split("function showParamSnackbar", 1)[1].split("}\n", 1)[0]
  assert "escapeSnackbarText(message)" in helper


def test_personality_cards_replace_legacy_follow_rows_without_changing_their_runtime_keys():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  advanced = source.split("const PERSONALITY_ADVANCED_KEYS = {", 1)[1].split("}\n", 1)[0]
  hidden = source.split("const HIDDEN_SETTING_KEYS = new Set([", 1)[1].split("]);", 1)[0]
  for key in (
    "TrafficFollow",
    "AggressiveFollow",
    "AggressiveFollowHigh",
    "StandardFollow",
    "StandardFollowHigh",
    "RelaxedFollow",
    "RelaxedFollowHigh",
  ):
    assert f'"{key}"' not in advanced
    assert f'"{key}"' in hidden


def test_each_personality_card_maps_to_its_persisted_enable_toggle():
  result = _run_node("""
    const paramKey = profiles.personalityProfileParamKey;
    console.log(JSON.stringify(typeof paramKey === "function" ?
      ["traffic", "aggressive", "standard", "relaxed"].map(paramKey) : ["missing helper"]));
  """)
  assert result == [
    "TrafficPersonalityProfile",
    "AggressivePersonalityProfile",
    "StandardPersonalityProfile",
    "RelaxedPersonalityProfile",
  ]


def test_each_personality_card_exposes_an_accessible_parked_only_enable_toggle():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  assert "function renderPersonalityProfileToggle" in source
  toggle = source.split("function renderPersonalityProfileToggle", 1)[1].split("\n}", 1)[0]
  assert "personalityProfileParamKey(profile.id)" in toggle
  assert 'aria-label="${param.label}"' in toggle
  assert 'checked="${() => !!state.values[param.key]}"' in toggle
  assert 'disabled="${() => lockReason() !== ""}"' in toggle
  assert 'updateParam(param.key, "checkbox")' in toggle
  card = source.split("function renderPersonalityCardSnapshot", 1)[1].split("\n}", 1)[0]
  assert "renderPersonalityProfileToggle(profile)" in card


def test_each_profile_enable_toggle_controls_only_its_card_editor_visibility():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  card = source.split("function renderPersonalityCardSnapshot", 1)[1].split("\n}", 1)[0]
  assert 'class="ds-personality-settings"' in card
  assert 'hidden="${() => !state.values[personalityProfileParamKey(profile.id)]}"' in card
  assert 'hidden="${() => !!state.values[personalityProfileParamKey(profile.id)]}"' in card
  assert "Turn on ${profile.label} to configure its profile." in card
  assert "settingsVisible ? html`" not in card


def test_profile_enable_toggles_remain_suppressed_from_the_generic_setting_list():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  marker = "const PROFILE_HIDDEN_LAYOUT_KEYS = new Set(["
  assert marker in source
  hidden = source.split(marker, 1)[1].split("]);", 1)[0]
  for key in (
    "TrafficPersonalityProfile",
    "AggressivePersonalityProfile",
    "StandardPersonalityProfile",
    "RelaxedPersonalityProfile",
  ):
    assert f'"{key}"' in hidden
  visibility = source.split("function isSettingVisible", 1)[1].split("\n}", 1)[0]
  assert "PROFILE_HIDDEN_LAYOUT_KEYS.has(param.key)" in visibility


def test_profile_presets_are_direct_neutral_buttons_not_dropdowns():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  field = source.split("function renderPersonalityCategoryField", 1)[1].split("\n}", 1)[0]
  assert "<select" not in field
  assert 'aria-pressed="${() => config.preset === option ? "true" : "false"}"' in field
  assert "updatePersonalityPreset(profile.id, category, option)" in field


def test_reselecting_custom_preset_is_a_noop_but_changed_presets_submit():
  result = _run_node("""
    const shouldSubmit = profiles.shouldSubmitPersonalityPreset;
    console.log(JSON.stringify(typeof shouldSubmit === "function" ? [
      shouldSubmit("custom", "custom"),
      shouldSubmit("standard", "custom"),
    ] : ["missing helper"]));
  """)
  assert result == [False, True]


def test_switching_to_custom_seeds_a_complete_reference_curve():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  update = source.split("function updatePersonalityPreset", 1)[1].split("\n}\n\nfunction resetPersonalityCurve", 1)[0]
  assert "state.personalityReferenceCurves?.[profileId]?.[category]" in update
  assert "Array.isArray(referenceCurve)" in update
  assert "selectedPreset, curve" in update


def test_graph_edits_still_submit_custom_curve_writes():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  drag = source.split("function beginPersonalityCurveDrag", 1)[1].split("\n}\n\nfunction setPersonalityCurveError", 1)[0]
  adjust = source.split("function adjustPersonalityCurvePoint", 1)[1].split("\n}\n\nfunction renderPersonalityCurve", 1)[0]
  assert 'savePersonalityCategory(profileId, category, "custom", curve' in drag
  assert 'savePersonalityCategory(profileId, category, "custom", curve' in adjust


def test_successful_profile_save_updates_existing_reactive_category():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  saver = source.split("async function savePersonalityCategory", 1)[1].split("\n}", 1)[0]
  assert "currentConfig.preset = savedConfig.preset" in saver
  assert "currentConfig.curve = [...savedConfig.curve]" in saver
  assert "state.personalityProfiles = data.profiles" not in saver


def test_first_successful_switch_to_custom_opens_the_profile_advanced_panel():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  saver = source.split("async function savePersonalityCategory", 1)[1].split("\n}", 1)[0]

  assert 'const wasCustom = currentConfig.preset === "custom"' in saver
  assert 'if (!wasCustom && savedConfig.preset === "custom")' in saver
  assert "state.personalityAdvancedExpanded = {" in saver
  assert "[profileId]: true" in saver


def test_personality_selectors_are_visible_without_profile_level_disclosure():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  card = source.split("function renderPersonalityCardSnapshot", 1)[1].split("\n}", 1)[0]

  assert "function renderPersonalitySummaryMeter" not in source
  assert "function togglePersonalityCard" not in source
  assert "ds-personality-pills" not in card
  assert "ds-personality-manage" not in card
  assert "${isOpen ? html`" not in card
  for category in ("acceleration", "braking", "following"):
    assert f'renderPersonalityCategoryField(profile, "{category}"' in card


def test_custom_graphs_render_only_inside_the_advanced_panel():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  card = source.split("function renderPersonalityCardSnapshot", 1)[1].split("\n}", 1)[0]
  advanced_rows = source.split("function renderPersonalityAdvancedRows", 1)[1].split("\n}", 1)[0]
  advanced = source.split("function renderPersonalityAdvanced(profile", 1)[1].split("\n}", 1)[0]

  assert "renderPersonalityCurve" not in card
  assert "renderPersonalityAdvanced(profile, config)" in card
  assert "renderPersonalityAdvancedRows(profile, config)" in advanced
  for category in ("acceleration", "braking", "following"):
    assert f'${{() => config.{category}.preset === "custom" ? renderPersonalityCurve(profile, "{category}", config.{category}) : ""}}' in advanced_rows


def test_personality_cards_remove_segmented_summary_and_manage_layout():
  css = DEVICE_SETTINGS_CSS_PATH.read_text(encoding="utf-8")
  summary = css.split(".ds-personality-summary {", 1)[1].split("}", 1)[0]

  for selector in (
    ".ds-personality-card.open",
    ".ds-personality-manage",
    ".ds-personality-pills",
    ".ds-personality-summary-meter",
    ".ds-personality-summary-bar",
  ):
    assert selector not in css
  assert "display: flex" in summary
  assert "grid-template" not in summary


def test_personality_controls_have_visible_keyboard_focus_styles():
  css = DEVICE_SETTINGS_CSS_PATH.read_text(encoding="utf-8")
  for selector in (
    ".ds-personality-option:focus-visible",
    ".ds-personality-advanced > button:focus-visible",
    ".ds-personality-advanced-choice:focus-visible",
    ".ds-personality-value input:focus-visible",
    ".ds-personality-custom-number input:focus-visible",
  ):
    assert selector in css


def test_custom_graph_has_reference_line_and_only_reset_action():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  curve = source.split("function renderPersonalityCurve", 1)[1].split("\n}", 1)[0]
  draw = source.split("function drawPersonalityCurve", 1)[1].split("\n}", 1)[0]
  assert "referenceCurve" in curve
  expected_label = "".join([
    'aria-label="${profile.label} ${definition.label} at ${formatProfileSpeed(geometry.speeds[index], !!state.values.IsMetric)} ',
    '${profileSpeedUnit(!!state.values.IsMetric)}, ${definition.valueUnit}"',
  ])
  assert expected_label in curve
  assert "referenceCurve" in draw
  assert "context.setLineDash([" in draw
  assert 'class="ds-personality-reference-key"' in curve
  assert "Dom default" in curve
  css = DEVICE_SETTINGS_CSS_PATH.read_text(encoding="utf-8")
  assert ".ds-personality-reference-key" in css
  assert "resetPersonalityCurve" in curve
  assert ">Reset<" in curve
  assert ">Copy<" not in curve
  assert ">Paste<" not in curve


def test_advanced_values_use_supported_presets_and_warn_before_custom():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  advanced_rows = source.split("function renderPersonalityAdvancedRows", 1)[1].split("\n}", 1)[0]
  value_editor = source.split("function renderPersonalityAdvancedValue", 1)[1].split("\n}", 1)[0]
  option_resolver = source.split("function personalityAdvancedOptions", 1)[1].split("\n}", 1)[0]
  advanced = advanced_rows + value_editor + option_resolver
  assert "Custom values are untested" in advanced
  assert "Chill" in advanced
  assert "Standard" in advanced
  assert "Custom" in advanced
  assert 'key.endsWith("JerkDanger")' in option_resolver
  assert '[["standard", "Standard"], ["custom", "Custom"]]' in option_resolver
  assert "renderSettingRow" not in advanced
  assert "updatePersonalityAdvancedPreset" in source
  assert "ds-personality-advanced-choice" in value_editor
  assert 'min="${bounds.min}"' in value_editor
  assert 'max="${bounds.max}"' in value_editor
  assert 'step="${bounds.step}"' in value_editor
  assert "resolveCurrentNumericValue(param, bounds)" in value_editor


def test_profile_descriptions_are_removed():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  assert "Stop-and-go driving" not in source
  assert "Assertive driving with tighter gaps" not in source
  assert "Balanced everyday driving" not in source
  assert "Smoother driving with larger gaps" not in source


def test_advanced_disclosure_uses_the_concise_advanced_label():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  advanced = source.split("function renderPersonalityAdvanced(profile, config)", 1)[1].split("\n}", 1)[0]
  assert "${isOpen ? \"Hide\" : \"Show\"} existing smoothness & response controls" not in advanced
  assert "\n        Advanced\n" in advanced


def test_advanced_disclosure_updates_in_place_without_rerendering_the_card():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  advanced = source.split("function renderPersonalityAdvanced(profile, config)", 1)[1].split("\n}", 1)[0]
  assert "const isOpen =" not in advanced
  assert 'aria-expanded="${() => state.personalityAdvancedExpanded[profile.id] ? "true" : "false"}"' in advanced
  assert "${renderPersonalityAdvancedRows(profile, config)}" in advanced
  rows = source.split("function renderPersonalityAdvancedRows(profile, config)", 1)[1].split("\n}", 1)[0]
  assert 'hidden="${() => !state.personalityAdvancedExpanded[profile.id]}"' in rows
  assert "PERSONALITY_ADVANCED_KEYS[profile.id]" in rows
  assert "renderPersonalityAdvancedValue" in rows
  assert "renderSettingRow" not in rows


def test_profiles_panel_omits_the_redundant_enabled_intro_and_toggle():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  panel = source.split("function renderPersonalityProfilesPanel()", 1)[1].split("\n}", 1)[0]
  assert "ds-personality-intro" not in panel
  assert "Use per-personality longitudinal profiles" not in panel
  assert "Acceleration, cruise/SLC braking" not in panel


def test_dom_default_is_not_offered_in_profile_selectors():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  field = source.split("function renderPersonalityCategoryField", 1)[1].split("\n}", 1)[0]
  assert '.filter(option => option !== "dom_default")' in field


def test_schema_migration_state_is_visible_and_blocks_profile_writes():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  assert "personalityMigrationRequired: false" in source
  assert "state.personalityMigrationRequired = !!data.migration_required" in source
  assert "This profile data requires a verified migration before it can be edited." in source
  assert "!!state.personalityMigrationRequired" in source
  assert 'param?.key === "CustomPersonalities" && state.personalityMigrationRequired' in source
  assert 'fetch("/api/personality_profiles/migrate", { method: "POST" })' in source
  assert "Migrate profiles" in source
  migration_warning = source.split('class="ds-personality-migration-warning"', 1)[1].split("</div>", 1)[0]
  assert '!state.values.IsOffroad' not in migration_warning
  assert '!!state.values.IsOnroad || state.personalityMigrationInProgress' in migration_warning
  css = DEVICE_SETTINGS_CSS_PATH.read_text(encoding="utf-8")
  assert ".ds-personality-migration-warning" in css


def test_all_personality_cards_start_collapsed():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  state_block = source.split("const state = reactive({", 1)[1].split("})", 1)[0]
  assert "personalityExpanded: {}," in state_block
  assert "personalityExpanded: { traffic: true }" not in state_block


def test_advanced_rows_are_hidden_by_author_css_when_collapsed():
  css = DEVICE_SETTINGS_CSS_PATH.read_text(encoding="utf-8")
  assert ".ds-personality-advanced-rows[hidden]" in css
  hidden_rule = css.split(".ds-personality-advanced-rows[hidden]", 1)[1].split("}", 1)[0]
  assert "display: none;" in hidden_rule


def test_personality_cards_keep_distinct_symbols_but_selectors_are_not_profile_coloured():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  css = DEVICE_SETTINGS_CSS_PATH.read_text(encoding="utf-8")
  for icon in ("bi-stoplights-fill", "bi-lightning-charge-fill", "bi-speedometer2", "bi-feather"):
    assert icon in source
  assert '<i class="${profile.icon}" aria-hidden="true"></i>' in source
  assert ".ds-personality-option[aria-pressed=\"true\"]" in css
  assert ".ds-personality-option[data-profile=" not in css


def test_custom_personalities_panel_excludes_its_legacy_subtree_from_rendering_and_search():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  sections = source.split("function getSectionsWithSlug()", 1)[1].split("\n}", 1)[0]
  tree = source.split("function renderSettingTree", 1)[1].split("\n}", 1)[0]
  assert "personalityLegacySubtreeKeys" in sections
  assert "!personalityLegacySubtreeKeys.has(param.key)" in sections
  assert 'if (param.key === "CustomPersonalities") continue' in tree


def test_device_settings_polls_driving_state_and_units_while_visible():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  assert "function ensureUiContextPolling" in source
  refresh = source.split("async function refreshUiContextValues", 1)[1].split("\n}", 1)[0]
  assert '["IsOnroad", "IsMetric"]' in refresh
  assert '`/api/params?key=${encodeURIComponent(key)}`' in refresh
  polling = source.split("function ensureUiContextPolling", 1)[1].split("\n}", 1)[0]
  assert 'document.visibilityState === "visible"' in polling
  component = source.split("export function DeviceSettings", 1)[1]
  assert "ensureUiContextPolling()" in component


def test_profile_load_errors_are_accurate_persistent_and_do_not_clear_migration_block():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  fetcher = source.split("async function fetchPersonalityProfiles", 1)[1].split("\n}", 1)[0]
  assert "personalityProfilesError" in fetcher
  assert "returned malformed data" in fetcher
  assert "state.personalityMigrationRequired = false" not in fetcher
  panel = source.split("function renderPersonalityProfilesPanel", 1)[1].split("\n}", 1)[0]
  assert "state.personalityProfilesError" in panel
  assert 'role="alert"' in panel
  assert 'aria-live="assertive"' in panel


def test_personality_cards_and_advanced_disclosures_have_unique_accessible_relationships():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  card = source.split("function renderPersonalityCardSnapshot", 1)[1].split("\n}", 1)[0]
  assert 'aria-labelledby="personality-heading-${profile.id}"' in card
  assert '<strong id="personality-heading-${profile.id}">${profile.label}</strong>' in card
  assert 'aria-controls="personality-body-${profile.id}"' not in card
  assert 'id="personality-body-${profile.id}"' in card
  assert "ds-personality-manage" not in card
  advanced = source.split("function renderPersonalityAdvanced(profile, config)", 1)[1].split("\n}", 1)[0]
  assert 'aria-controls="personality-advanced-${profile.id}"' in advanced
  assert 'id="personality-advanced-${profile.id}"' in source
  assert 'aria-hidden="true"' in advanced
  manage = source.split('${() => p.is_parent_toggle', 1)[1].split("` : \"\"}", 1)[0]
  assert 'aria-controls="${p.key === "CustomPersonalities" ? "personality-profiles-panel"' in manage
  assert 'aria-expanded="${() => state.expanded[p.key] ? "true" : "false"}"' in manage


def test_nested_manage_panels_render_through_a_reactive_child_expression():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  tree = source.split("function renderSettingTree(paramsList, parentKey = null)", 1)[1].split("\n}", 1)[0]

  assert "${() => renderSettingTree(paramsList, param.key)}" in tree


def test_personality_control_names_include_profile_category_and_units():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  curve = source.split("function renderPersonalityCurve", 1)[1].split("\n}", 1)[0]
  assert 'aria-label="Reset ${profile.label} ${definition.label} graph to Dom default"' in curve
  assert '${definition.valueUnit}' in curve.split('aria-label="${profile.label} ${definition.label} at', 1)[1].split('"', 1)[0]
  advanced = source.split("function renderPersonalityAdvancedValue", 1)[1].split("\n}", 1)[0]
  assert "profile.label" in advanced
  assert "percentage" in advanced
  assert 'aria-label="${profile.label} ${param.label} custom percentage"' in advanced


def test_snackbars_expose_polite_status_and_assertive_error_live_regions():
  source = SNACKBAR_PATH.read_text(encoding="utf-8")
  assert 'level === "error" ? "alert" : "status"' in source
  assert 'level === "error" ? "assertive" : "polite"' in source


def test_graph_number_edits_use_native_validity_and_keep_persistent_inline_errors():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  adjust = source.split("function adjustPersonalityCurvePoint", 1)[1].split("\n}", 1)[0]
  assert "input.valueAsNumber" in adjust
  assert "input.validity.valid" in adjust
  assert "Number.isFinite" in adjust
  invalid_branch = adjust.split("if (!raw || !input.validity.valid || !Number.isFinite(parsed)) {", 1)[1].split("return\n  }", 1)[0]
  assert "savePersonalityCategory" not in invalid_branch
  assert "setPersonalityCurveError" in invalid_branch
  curve = source.split("function renderPersonalityCurve", 1)[1].split("\n}", 1)[0]
  assert "state.personalityCurveErrors[updateKey]" in curve
  assert 'role="alert"' in curve
  assert 'aria-live="assertive"' in curve
  assert '@change="${event => adjustPersonalityCurvePoint(profile.id, category, index, event.currentTarget)}"' in curve


def test_failed_graph_put_restores_persisted_curve_inputs_and_canvas_for_edit_and_drag():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  assert "function restorePersonalityCurveVisual" in source
  restore = source.split("function restorePersonalityCurveVisual", 1)[1].split("\n}", 1)[0]
  assert "drawPersonalityCurve" in restore
  assert "personality-input-${profileId}-${category}-${index}" in restore
  assert "personality-value-${profileId}-${category}-${index}" in restore
  drag = source.split("function beginPersonalityCurveDrag", 1)[1].split("\n}\n\nfunction setPersonalityCurveError", 1)[0]
  assert "if (!saved) restorePersonalityCurveVisual" in drag
  adjust = source.split("function adjustPersonalityCurvePoint", 1)[1].split("\n}\n\nfunction renderPersonalityCurve", 1)[0]
  assert "if (!saved) restorePersonalityCurveVisual" in adjust


def test_personality_jerk_layout_metadata_matches_stored_percentage_range():
  layout = json.loads(DEVICE_SETTINGS_LAYOUT_PATH.read_text(encoding="utf-8"))
  jerk_params = [
    param
    for section in layout
    for param in section.get("params", [])
    if any(param.get("key", "").startswith(profile) for profile in ("Traffic", "Aggressive", "Standard", "Relaxed"))
    and "Jerk" in param.get("key", "")
  ]
  assert len(jerk_params) == 20
  assert all((param.get("min"), param.get("max"), param.get("step")) == (25, 200, 1) for param in jerk_params)


def test_graph_geometry_accepts_rendered_width_without_changing_saved_bounds():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  geometry_function = "function graphGeometry" + source.split("function graphGeometry", 1)[1].split("\n}\n", 1)[0] + "\n}"
  result = _run_node("""
    const state = {personalityMeta:{bounds:{acceleration:[0,3.5]},speedBreakpointsMph:{acceleration:[0,90]}}};
  """ + geometry_function + """
    console.log(JSON.stringify([224,280,660,750].map(width => {
      const g=graphGeometry("acceleration", [6,6], width);
      return {width:g.width, endpoints:[g.x(0),g.x(1)], bounds:g.bounds};
    })));
  """)
  assert result == [{"width": width, "endpoints": [46, width - 22], "bounds": [0, 6]} for width in (224, 280, 660, 750)]


def test_personality_responsive_layout_uses_available_card_width():
  css = DEVICE_SETTINGS_CSS_PATH.read_text(encoding="utf-8")
  assert "container-type: inline-size" in css
  assert "@container (max-width: 850px)" in css
  assert "repeat(auto-fit, minmax(min(100%, 260px), 1fr))" in css
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  assert "canvas.clientWidth" in source
  assert 'context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)' in source


def test_personality_save_blocks_onroad_even_for_synthetic_events():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  save = "async function savePersonalityCategory" + source.split("async function savePersonalityCategory", 1)[1].split("\n}\n", 1)[0] + "\n}"
  result = _run_node("""
    const state = {values:{IsOnroad:true}};
    const fetch = () => {throw new Error("On-road write attempted")};
  """ + save + """
    console.log(JSON.stringify(await savePersonalityCategory("standard", "acceleration", "eco", [])));
  """)
  assert result is False


def test_responsive_canvas_keeps_metric_endpoint_labels_separate_and_scales_bitmap():
  source = DEVICE_SETTINGS_PATH.read_text(encoding="utf-8")
  functions = "\n".join(
    "function " + name + source.split("function " + name, 1)[1].split("\n}\n", 1)[0] + "\n}"
    for name in ("graphGeometry", "curveTicks", "drawPersonalityCurve")
  )
  result = _run_node("""
    const state = {values:{IsMetric:true},personalityMeta:{bounds:{acceleration:[0,3.5]},
      speedBreakpointsMph:{acceleration:[0,10,20,30,40,50,60,70,80,90]}}};
    const PERSONALITY_CATEGORY_DEFINITIONS={acceleration:{valueUnit:"m/s²",step:0.01}};
    const window={devicePixelRatio:2};
    const labels=[], transforms=[];
    const context=new Proxy({
      measureText:text=>({width:String(text).length*5}),
      fillText:(text,x,y)=>{if(y===227) labels.push({text,x,width:String(text).length*5});},
      setTransform:(...args)=>transforms.push(args),
    },{get:(target,key)=>target[key] || (()=>{})});
    class HTMLCanvasElement {clientWidth=261; getContext(){return context;}}
  """ + functions + """
    const canvas=new HTMLCanvasElement(), curve=Array(10).fill(6);
    drawPersonalityCurve(canvas,"acceleration",curve);
    console.log(JSON.stringify({labels,transforms,width:canvas.width,height:canvas.height,curve}));
  """)
  assert (result["width"], result["height"]) == (522, 480)
  assert result["transforms"] == [[2, 0, 0, 2, 0, 0]]
  assert result["curve"] == [6] * 10
  labels = result["labels"]
  assert [labels[0]["text"], labels[-1]["text"]] == ["0", "144.8"]
  for left, right in zip(labels, labels[1:]):
    assert left["x"] + left["width"] / 2 + 6 <= right["x"] - right["width"] / 2
