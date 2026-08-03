#!/usr/bin/env python3
"""
derive_feasible_params.py

Dynamically parses the OpenPilot/StarPilot codebase to cross-reference logically
registered Param keys with UI string literals. This ensures that no hidden or
dynamically-instantiated UI toggles are missed, outputting a highly accurate "Golden List"
of parameters that can be safely modified by The Galaxy or other configuration interfaces.
"""

import os
import re

def get_repo_root() -> str:
    # Resolves to the root of the StarPilot repository based on this script's location
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))

# Constants
REPO_ROOT = get_repo_root()
PARAMS_KEYS_PATH = os.path.join(REPO_ROOT, 'common/params_keys.h')
UI_DIRECTORIES = [
    os.path.join(REPO_ROOT, 'selfdrive/ui'),
    os.path.join(REPO_ROOT, 'starpilot/ui')
]

# A curated list of parameters that are known to be strictly readable state metadata
# rather than user-toggled configurations.
KNOWN_READ_ONLY = {
    "ApiCache_Device", "ApiCache_DriveStats", "ApiCache_NavDestinations",
    "CCStatus", "CEStatus",
    "CarMake", "CarModel", "CarModelName", "CarParamsPersistent", "CarVin",
    "ClusterOffset", "Compass", "DeveloperSidebarMetric1", "DeveloperSidebarMetric2",
    "DeveloperSidebarMetric3", "DeveloperSidebarMetric4", "DeveloperSidebarMetric5",
    "DeveloperSidebarMetric6", "DeveloperSidebarMetric7", "DongleId",
    "FLMActiveOverrides", "FLMActiveProfileId", "FLMTrialApplied", "FLMTrialBaseline",
    "StarPilotCarParamsPersistent", "StarPilotDrives", "StarPilotKilometers",
    "StarPilotMinutes", "GitBranch", "GitCommit", "GitCommitDate", "GitDiff",
    "GitRemote", "GithubSshKeys", "GithubUsername", "HardwareSerial", "IMEI",
    "InstallDate", "IsRhdDetected", "KonikMinutes", "LastGPSPosition",
    "LastMapsUpdate", "LastUpdateTime", "ModelDrivesAndScores", "ModelReleasedDates",
    "ModelVersions", "PersistedCCStatus", "PersistedCEStatus", "PrimeType",
    "TermsVersion", "TrainingVersion", "Version",
    "openpilotMinutes", "CompletedTrainingVersion"
}

GALAXY_ONLY_PARAMS = {
    "LatSmoothSeconds", "LongSmoothSeconds",
}

def extract_registered_keys(params_path: str) -> set:
    """Extracts all legally registered parameter keys from common/params_keys.h"""
    registered_keys = set()
    try:
        with open(params_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Isolate the registered keys block.
        keys_block_match = re.search(r'keys\s*=\s*\{(.*?)\n\};', content, re.DOTALL)
        if not keys_block_match:
            print("Error: Could not locate 'keys' map in params_keys.h")
            return registered_keys

        # Extract {"KeyName", {FLAGS...}} entries.
        for match in re.finditer(r'\{"([A-Za-z0-9_]+)",\s*\{([^}]*)\}\s*\}', keys_block_match.group(1)):
            key, flag = match.group(1), match.group(2)
            # Remove keys that are strictly internal ephemeral states
            if 'CLEAR_ON_MANAGER_START' not in flag:
                registered_keys.add(key)

    except FileNotFoundError:
        print(f"Error: Could not find params source file at {params_path}")

    return registered_keys

def extract_ui_string_literals(ui_dirs: list) -> set:
    """Recursively walks UI directories to extract every string literal."""
    ui_strings = set()
    valid_extensions = ('.cc', '.h', '.cpp', '.hpp', '.qml')

    for directory in ui_dirs:
        if not os.path.exists(directory):
            print(f"Warning: UI directory not found {directory}")
            continue

        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(valid_extensions):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        # Extract all "StringLiterals" block
                        matches = re.findall(r'\"([A-Za-z0-9_]+)\"', f.read())
                        ui_strings.update(matches)

    return ui_strings

def main():
    print(f"Starting parameter derivation inside {REPO_ROOT}...")

    # 1. Fetch
    registered_keys = extract_registered_keys(PARAMS_KEYS_PATH)
    ui_strings = extract_ui_string_literals(UI_DIRECTORIES)

    # 2. Intersect
    feasible_keys = registered_keys.intersection(ui_strings)

    # 3. Filter Read-Only
    editable_keys = (feasible_keys | GALAXY_ONLY_PARAMS) - KNOWN_READ_ONLY

    # 4. Export
    output_path = os.path.join(os.path.dirname(__file__), 'feasibleparams.txt')
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("Dynamically Derived Feasible Param Candidates (The Golden List)\n")
            f.write("===============================================================\n\n")
            f.write(f"Total globally registered C++ keys:  {len(registered_keys)}\n")
            f.write(f"Total explicit UI string references: {len(feasible_keys)}\n")
            f.write(f"Total Editable/Toggleable targets:   {len(editable_keys)}\n\n")

            for key in sorted(list(editable_keys)):
                f.write(f"{key}\n")

        print(f"Successfully derived {len(editable_keys)} highly feasible parameter targets.")
        print(f"Report exported to: {output_path}")
    except Exception as e:
        print(f"Error writing to output file: {e}")

if __name__ == '__main__':
    main()
