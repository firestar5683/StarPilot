import os
import re
import sys
import json
import ast

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))

CATEGORIES = [
    {"file": "lateral_settings.cc", "name": "Lateral (Steering)", "icon": "bi-arrows-move"},
    {"file": "longitudinal_settings.cc", "name": "Longitudinal (Speed & Following)", "icon": "bi-speedometer2"},
    {"file": "visual_settings.cc", "name": "Visual (Display & UI)", "icon": "bi-eye"},
    {"file": "sounds_settings.cc", "name": "Sounds & Alerts", "icon": "bi-volume-up"},
    {"file": "vehicle_settings.cc", "name": "Vehicle", "icon": "bi-car-front"},
    {"file": "device_settings.cc", "name": "Device & Data", "icon": "bi-hdd"},
]

DROPDOWN_MAPPING = {
    "SelectModel": {
        "key": "DrivingModel",
        "options_endpoint": "/api/models/installed"
    }
}

# Custom controls implemented outside the tuple vectors in Qt settings panels.
# Inject these so regenerated galaxy layouts retain equivalent functionality.
INJECTED_SECTION_PARAMS = {
    "Longitudinal (Speed & Following)": [
        {
            "key": "LongitudinalModelPreference",
            "label": "Longitudinal Preference",
            "description": "Set-Speed First prioritizes steady cruise on open roads. Model First gives the driving model more influence. Both use the same lead and stop safety.",
            "data_type": "int",
            "ui_type": "dropdown",
            "options": [
                {"value": 0, "label": "Set-Speed First"},
                {"value": 1, "label": "Model First"},
            ],
        },
        {
            "key": "ShowCEMStatus",
            "label": "Longitudinal Status",
            "description": "Show which constraint is currently influencing the unified longitudinal planner.",
            "data_type": "bool",
            "ui_type": "toggle",
        },
    ],
    "Vehicle": [
        {
            "key": "CarMake",
            "label": "Car Make",
            "description": "Select your car make.",
            "data_type": "string",
            "ui_type": "dropdown",
            "options_endpoint": "/api/fingerprints/makes",
        },
        {
            "key": "CarModel",
            "label": "Car Model (Fingerprint)",
            "description": "Choose the fingerprint platform to use when automatic detection is disabled.",
            "data_type": "string",
            "ui_type": "dropdown",
            "options_endpoint": "/api/fingerprints/models?make={CarMake}",
        },
        {
            "key": "ForceFingerprint",
            "label": "Disable Automatic Fingerprint Detection",
            "description": "Force the selected fingerprint and prevent it from changing automatically.",
            "data_type": "bool",
            "ui_type": "toggle",
        },
        {
            "key": "IsRHD",
            "label": "Right Hand Driving",
            "description": "Use right-hand-drive driver monitoring. This follows the auto-detected side until changed manually.",
            "data_type": "bool",
            "ui_type": "toggle",
        },
    ],
}

# Keys explicitly hidden from The Galaxy's generic settings UI.
HIDDEN_KEYS = {
    "CCMLaunchAssist",
    "CCMLead",
    "CCMSetSpeedMargin",
    "CCMSpeed",
    "CCMSpeedLead",
    "CECurves",
    "CECurvesLead",
    "CELead",
    "CEModelStopTime",
    "CESignalLaneDetection",
    "CESignalSpeed",
    "CESlowerLead",
    "CESpeed",
    "CESpeedLead",
    "CEStopLights",
    "CEStoppedLead",
    "ConditionalChill",
    "ConditionalExperimental",
    "FrogsGoMoosTweak",
    "HumanAcceleration",
    "DisableWideRoad",
    "LockDoorsTimer",
    "NewLongAPI",
    "PersistChillState",
    "PersistExperimentalState",
    "ReverseCruise",
    "ShowCCMStatus",
    "ShowCEMStatus",
    "ToyotaDoors",
}

HIDDEN_SECTION_NAMES = {"Model & Customization"}

# Keys that are boolean toggles despite ambiguous defaults in starpilot_variables.py.
FORCE_BOOL_KEYS = {"EVTuning"}


def get_param_settings_tiers():
    params_path = os.path.join(REPO_ROOT, "common/params_keys.h")
    tiers = {}
    with open(params_path, "r", encoding="utf-8") as params_file:
        for line in params_file:
            match = re.match(r'\s*\{"([^"]+)",', line)
            if match:
                tiers[match.group(1)] = "simple" if "SETTINGS_SIMPLE" in line else "advanced"
    return tiers


PARAM_SETTINGS_TIERS = get_param_settings_tiers()


def apply_settings_tiers(layout):
    for section in layout:
        params = section.get("params", [])
        params_by_key = {param["key"]: param for param in params if "key" in param}
        resolved = {}

        def resolve_tier(key, resolving=None):
            if key in resolved:
                return resolved[key]

            resolving = set(resolving or ())
            if key in resolving:
                return "advanced"
            resolving.add(key)

            parent_key = params_by_key.get(key, {}).get("parent_key")
            own_tier = PARAM_SETTINGS_TIERS.get(key)
            if parent_key:
                parent_tier = resolve_tier(parent_key, resolving)
                resolved[key] = parent_tier if own_tier is None else (
                    "advanced" if "advanced" in (parent_tier, own_tier) else "simple"
                )
            else:
                resolved[key] = own_tier or "advanced"
            return resolved[key]

        for param in params:
            key = param.get("key")
            if key:
                param["settings_tier"] = resolve_tier(key)

    return layout

DEVELOPER_SIDEBAR_METRIC_KEYS = {
    "DeveloperSidebarMetric1",
    "DeveloperSidebarMetric2",
    "DeveloperSidebarMetric3",
    "DeveloperSidebarMetric4",
    "DeveloperSidebarMetric5",
    "DeveloperSidebarMetric6",
    "DeveloperSidebarMetric7",
}

DEVELOPER_SIDEBAR_METRIC_OPTIONS = [
    {"value": 0, "label": "None"},
    {"value": 1, "label": "Acceleration: Current"},
    {"value": 2, "label": "Acceleration: Max"},
    {"value": 3, "label": "Auto Tune: Actuator Delay"},
    {"value": 4, "label": "Auto Tune: Friction"},
    {"value": 5, "label": "Auto Tune: Lateral Acceleration"},
    {"value": 6, "label": "Auto Tune: Steer Ratio"},
    {"value": 7, "label": "Auto Tune: Stiffness Factor"},
    {"value": 8, "label": "Engagement %: Lateral"},
    {"value": 9, "label": "Engagement %: Longitudinal"},
    {"value": 10, "label": "Lateral Control: Steering Angle"},
    {"value": 11, "label": "Lateral Control: Torque % Used"},
    {"value": 12, "label": "Longitudinal Control: Actuator Acceleration Output"},
    {"value": 13, "label": "Longitudinal MPC Jerk: Acceleration"},
    {"value": 14, "label": "Longitudinal MPC Jerk: Danger Zone"},
    {"value": 15, "label": "Longitudinal MPC Jerk: Speed Control"},
    {"value": 16, "label": "Driving Model: Current"},
]

PARENT_KEYS_MAPPING = {
    "device_settings.cc": {
        "deviceManagementKeys": "DeviceManagement",
        "screenKeys": "ScreenManagement"
    },
    "lateral_settings.cc": {
        "advancedLateralTuneKeys": "AdvancedLateralTune",
        "aolKeys": "AlwaysOnLateral",
        "laneChangeKeys": "LaneChanges",
        "lateralTuneKeys": "LateralTune",
        "qolKeys": "QOLLateral"
    },
    "longitudinal_settings.cc": {
        "advancedLongitudinalTuneKeys": "AdvancedLongitudinalTune",
        "aggressivePersonalityKeys": "AggressivePersonalityProfile",
        "curveSpeedKeys": "CurveSpeedController",
        "customDrivingPersonalityKeys": "CustomPersonalities",
        "longitudinalTuneKeys": "LongitudinalTune",
        "qolKeys": "QOLLongitudinal",
        "relaxedPersonalityKeys": "RelaxedPersonalityProfile",
        "speedLimitControllerKeys": "SpeedLimitController",
        "speedLimitControllerOffsetsKeys": "SpeedLimitController",
        "speedLimitControllerQOLKeys": "SpeedLimitController",
        "speedLimitControllerVisualKeys": "SpeedLimitController",
        "standardPersonalityKeys": "StandardPersonalityProfile",
        "trafficPersonalityKeys": "TrafficPersonalityProfile"
    },
    "sounds_settings.cc": {
        "alertVolumeControlKeys": "AlertVolumeControl",
        "customAlertsKeys": "CustomAlerts"
    },
    "theme_settings.cc": {
        "customThemeKeys": "CustomTheme"
    },
    "visual_settings.cc": {
        "advancedCustomOnroadUIKeys": "AdvancedCustomUI",
        "customOnroadUIKeys": "CustomUI",
        "developerMetricKeys": "DeveloperMetrics",
        "developerSidebarKeys": "DeveloperSidebar",
        "developerUIKeys": "DeveloperUI",
        "developerWidgetKeys": "DeveloperWidgets",
        "modelUIKeys": "ModelUI",
        "navigationUIKeys": "NavigationUI",
        "qualityOfLifeKeys": "QOLVisuals"
    },
    "vehicle_settings.cc": {}
}

ALL_PARENT_KEYS = set()
for cmap in PARENT_KEYS_MAPPING.values():
    for parent in cmap.values():
        ALL_PARENT_KEYS.add(parent)

def get_variables_data():
    filepath = os.path.join(REPO_ROOT, "starpilot/common/starpilot_variables.py")
    excluded = set()
    defaults = {}
    if not os.path.exists(filepath):
        return excluded, defaults

    with open(filepath, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())

    def parse_params_list(value_node):
        try:
            if isinstance(value_node, ast.List):
                for elt in value_node.elts:
                    if isinstance(elt, ast.Tuple) and len(elt.elts) >= 2:
                        key_node = elt.elts[0]
                        val_node = elt.elts[1]
                        if isinstance(key_node, ast.Constant):
                            key = key_node.value
                            if isinstance(val_node, ast.Constant):
                                val = val_node.value
                                if isinstance(val, (str, bytes)):
                                    v = val.decode('utf-8') if isinstance(val, bytes) else str(val)
                                    if v in ("0", "1"):
                                        defaults[key] = "bool"
                                    elif "." in v and v.replace(".", "", 1).isdigit():
                                        defaults[key] = "float"
                                    elif v.isdigit():
                                        defaults[key] = "int"
                                    else:
                                        defaults[key] = "string"
                                else:
                                    defaults[key] = "unknown"
                            elif isinstance(val_node, ast.Call) and isinstance(val_node.func, ast.Name) and val_node.func.id == "str":
                                # str(<numeric expression>) is used for several numeric defaults.
                                defaults[key] = "float"
                            else:
                                defaults[key] = "unknown"
        except:
            pass

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if getattr(target, 'id', '') == 'EXCLUDED_KEYS':
                    try:
                        excluded = ast.literal_eval(node.value)
                    except:
                        pass
                elif getattr(target, 'id', '') in ('starpilot_default_params', 'misc_tuning_levels'):
                    parse_params_list(node.value)
        elif isinstance(node, ast.AnnAssign):
            if getattr(node.target, 'id', '') in ('starpilot_default_params', 'misc_tuning_levels'):
                parse_params_list(node.value)

    return excluded, defaults

EXCLUDED_KEYS, DEFAULT_TYPES = get_variables_data()

def get_editable_keys():
    filepath = os.path.join(REPO_ROOT, "starpilot/common/starpilot_variables.py")
    editable = set()
    if not os.path.exists(filepath):
        return editable

    with open(filepath, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())

    for node in tree.body:
        value_node = None
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if getattr(target, 'id', '') == 'starpilot_default_params':
                    value_node = node.value
                    break
        elif isinstance(node, ast.AnnAssign):
            if getattr(node.target, 'id', '') == 'starpilot_default_params':
                value_node = node.value

        if isinstance(value_node, ast.List):
            for elt in value_node.elts:
                if isinstance(elt, ast.Tuple) and elt.elts and isinstance(elt.elts[0], ast.Constant):
                    editable.add(elt.elts[0].value)

    return editable

EDITABLE_KEYS = get_editable_keys()


def parse_params_keys_h():
    filepath = os.path.join(REPO_ROOT, "common/params_keys.h")
    keys = set()
    types = {}
    if not os.path.exists(filepath):
        return keys, types

    type_map = {
        "BOOL": "bool",
        "INT": "int",
        "FLOAT": "float",
        "STRING": "string",
        "JSON": "string",
        "BYTES": "string",
    }
    pattern = re.compile(r'\{"([A-Za-z0-9_]+)",\s*\{[^,]+,\s*([A-Z]+)')

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            match = pattern.search(line)
            if not match:
                continue
            key, ptype = match.groups()
            keys.add(key)
            types[key] = type_map.get(ptype, "unknown")

    return keys, types


if not DEFAULT_TYPES or not EDITABLE_KEYS:
    parsed_keys, parsed_types = parse_params_keys_h()
    if not EDITABLE_KEYS:
        EDITABLE_KEYS = parsed_keys
    for key, value in parsed_types.items():
        DEFAULT_TYPES.setdefault(key, value)

def get_param_type(key):
    return DEFAULT_TYPES.get(key, "unknown")

def extract_bracket_block(text, start_idx):
    if text[start_idx] != '{': return ""
    depth = 0
    in_str = False
    escape = False
    for i in range(start_idx, len(text)):
        char = text[i]
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
        if char == '"':
            in_str = not in_str
            continue
        if not in_str:
            if char == '{': depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start_idx:i+1]
    return ""

def parse_cpp_file(filename):
    filepath = os.path.join(REPO_ROOT, "starpilot/ui/qt/offroad", filename)
    if not os.path.exists(filepath): return []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    vector_match = re.search(
        r'(?:const\s+)?std::vector<\s*std::tuple<QString,\s*QString,\s*QString,\s*QString>\s*>\s*\w+\s*\{',
        content,
        re.DOTALL,
    )
    if not vector_match: return []

    start_idx = vector_match.end() - 1
    vector_content = extract_bracket_block(content, start_idx)

    local_parent_map = PARENT_KEYS_MAPPING.get(filename, {})
    child_to_parent = {}
    child_to_qsets = {}

    header_filename = filename.replace(".cc", ".h")
    header_filepath = os.path.join(REPO_ROOT, "starpilot/ui/qt/offroad", header_filename)
    full_source = content
    if os.path.exists(header_filepath):
        with open(header_filepath, 'r', encoding='utf-8') as fh:
            full_source += "\n" + fh.read()

    for qset_match in re.finditer(r'QSet<QString>\s+(\w+)\s*(?:=\s*)?\{([^}]+)\};', full_source):
        qset_name = qset_match.group(1)
        if qset_name in local_parent_map:
            parent_key = local_parent_map[qset_name]
            children_str = qset_match.group(2)
            children = [c.strip().strip('"') for c in children_str.split(',') if c.strip()]
            for child in children:
                child_to_parent[child] = parent_key
                child_to_qsets.setdefault(child, []).append(qset_name)

    items = []

    idx = 0
    while True:
        idx = vector_content.find('{"', idx)
        if idx == -1: break

        block = extract_bracket_block(vector_content, idx)
        if not block:
            idx += 1
            continue

        row_match = re.search(r'\{"([A-Za-z0-9_]+)"\s*,\s*(.*?)\s*\}$', block, re.DOTALL)
        if not row_match:
            idx += len(block)
            continue

        key = row_match.group(1)
        rest = row_match.group(2)
        idx += len(block)

        if key in HIDDEN_KEYS or key in EXCLUDED_KEYS or key.startswith("IgnoreMe"):
            continue

        strings = re.findall(r'tr\("((?:[^"\\]|\\.)+)"\)|"((?:[^"\\]|\\.)+)"', rest)
        valid_strings = [s[0] or s[1] for s in strings if s[0] or s[1]]

        if not valid_strings: continue

        title = valid_strings[0]
        desc = valid_strings[1] if len(valid_strings) > 1 else ""
        options_endpoint = None
        dropdown_options = None

        if key in DEVELOPER_SIDEBAR_METRIC_KEYS:
            if key not in EDITABLE_KEYS:
                continue
            widget_type = "dropdown"
            data_type = "int"
            dropdown_options = DEVELOPER_SIDEBAR_METRIC_OPTIONS
        elif key in DROPDOWN_MAPPING:
            m = DROPDOWN_MAPPING[key]
            key = m["key"]
            widget_type = "dropdown"
            options_endpoint = m["options_endpoint"]
            data_type = "string"
        else:
            if key not in EDITABLE_KEYS:
                continue
            data_type = get_param_type(key)
            if data_type == "unknown": continue
            widget_type = "toggle"
            min_val, max_val, step = None, None, None

        for i in range(1, 10):
            placeholder = f"%{i}"
            if placeholder in desc and len(valid_strings) > i + 1:
                desc = desc.replace(placeholder, valid_strings[i + 1])

        desc = re.sub(r'<br\s*/?>', '\n', desc, flags=re.IGNORECASE)
        desc = re.sub(r'<[^>]+>', '', desc)
        desc = desc.replace('\\"', '"').strip()
        title = re.sub(r'\s*\(\s*Default:\s*%\d\s*\)', '', title)
        title = re.sub(r'%\d', '', title).strip()
        desc = re.sub(r'\s*\(\s*Default:\s*%\d\s*\)', '', desc)
        desc = re.sub(r'%\d', '', desc).strip()

        if widget_type == "toggle":
            snippet_match = None

            # Let's match the original's regex for finding the Toggle = assignment line
            search_patterns = [r'param\s*==\s*"' + key + r'"']
            for qset_name in child_to_qsets.get(key, []):
                search_patterns.append(r'(?:' + qset_name + r'\.contains\(param\))')

            for pattern in search_patterns:
                match = re.search(pattern + r'.*?[a-zA-Z]+Toggle\s*=\s*(.*?);', content, re.DOTALL)
                if match:
                    snippet_match = match
                    break

            if snippet_match:
                assignment = snippet_match.group(1)
                if "StarPilotParamValueControl" in assignment or "StarPilotParamValueButtonControl" in assignment:
                    widget_type = "numeric"
                    if data_type in ("string", "bool", "unknown"):
                        data_type = "float"

                    if "alertVolumeControlKeys" in child_to_qsets.get(key, []):
                        if key in ["WarningImmediateVolume", "WarningSoftVolume"]:
                            min_val, max_val, step = "25", "101", "1"
                        else:
                            min_val, max_val, step = "0", "101", "1"
                    else:
                        args_match = re.search(r'Control[^(]*\(([^;]+)\)', assignment)
                        if args_match:
                            args_str = args_match.group(1)
                            num_match = re.search(r'icon\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,(?:[^,]*,){2}\s*([-\d.]+)', args_str)
                            if num_match:
                                min_val, max_val, step = num_match.group(1), num_match.group(2), num_match.group(3)
                            else:
                                num_match = re.search(r'icon\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)', args_str)
                                if num_match:
                                    min_val, max_val = num_match.group(1), num_match.group(2)
                            step_match = re.search(r'(?:std::map<float,\s*QString>\(\)|[a-zA-Z0-9_]+Labels)\s*,\s*([-\d.]+)', args_str)
                            if step_match:
                                step = step_match.group(1)

        # CESpeed/CCMSpeed are rendered in Qt with dual numeric controls,
        # so the generic assignment matcher cannot infer it reliably.
        if key in {"CESpeed", "CCMSpeed"}:
            widget_type = "numeric"
            data_type = "int"
            min_val, max_val, step = "0", "99", "1"

        if key in FORCE_BOOL_KEYS:
            data_type = "bool"

        precision = None
        precision_match = re.search(r"QString::number\([^,]+,\s*'f'\s*,\s*(\d+)\)", rest)
        if precision_match:
            precision = int(precision_match.group(1))

        if data_type == "float" and step and float(step).is_integer():
             data_type = "int"

        # Generic galaxy UI can't faithfully represent non-boolean button/multi-option controls.
        if widget_type == "toggle" and data_type != "bool":
            continue

        s = {
            "key": key,
            "label": title,
            "description": desc,
            "data_type": data_type,
            "ui_type": widget_type
        }
        if widget_type == "numeric":
            if min_val is not None: s["min"] = float(min_val)
            if max_val is not None: s["max"] = float(max_val)
            if step is not None: s["step"] = float(step)
            if precision is not None: s["precision"] = precision
        elif widget_type == "dropdown":
            if options_endpoint: s["options_endpoint"] = options_endpoint
            if dropdown_options: s["options"] = dropdown_options
        if key in child_to_parent: s["parent_key"] = child_to_parent[key]
        if key in ALL_PARENT_KEYS: s["is_parent_toggle"] = True

        items.append(s)

    return items


def merge_layouts(existing_layout, generated_layout):
    existing_sections = {section["name"]: section for section in existing_layout}
    generated_sections = {section["name"]: section for section in generated_layout}

    merged_layout = []

    for section in existing_layout:
        name = section["name"]
        if name in HIDDEN_SECTION_NAMES:
            continue
        generated = generated_sections.get(name)
        if generated is None:
            merged_layout.append(section)
            continue

        existing_params = section.get("params", [])
        generated_params = generated.get("params", [])
        generated_by_key = {param["key"]: param for param in generated_params}

        merged_params = []
        seen_keys = set()

        for param in existing_params:
            key = param["key"]
            if key in generated_by_key:
                merged_params.append(generated_by_key[key])
            else:
                merged_params.append(param)
            seen_keys.add(key)

        for param in generated_params:
            key = param["key"]
            if key not in seen_keys:
                merged_params.append(param)
                seen_keys.add(key)

        merged_section = dict(section)
        merged_section["icon"] = generated.get("icon", section.get("icon"))
        merged_section["params"] = merged_params
        merged_layout.append(merged_section)

    existing_names = {section["name"] for section in existing_layout}
    for section in generated_layout:
        if section["name"] not in existing_names:
            merged_layout.append(section)

    return merged_layout

def main():
    generated_layout = []
    for cat in CATEGORIES:
        items = parse_cpp_file(cat["file"])
        injected = INJECTED_SECTION_PARAMS.get(cat["name"], [])
        if injected:
            existing_keys = {item["key"] for item in items}
            items = [dict(item) for item in injected if item["key"] not in existing_keys] + items
        if items:
            generated_layout.append({
                "name": cat["name"],
                "icon": cat["icon"],
                "params": items
            })
    output_path = os.path.join(REPO_ROOT, "starpilot/system/the_galaxy/assets/components/tools/device_settings_layout.json")
    layout = generated_layout
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            existing_layout = json.load(f)
        layout = merge_layouts(existing_layout, generated_layout)
    layout = apply_settings_tiers(layout)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(layout, f, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    main()
