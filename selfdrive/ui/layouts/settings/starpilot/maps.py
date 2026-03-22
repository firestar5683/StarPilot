from __future__ import annotations
import os
import shutil
from pathlib import Path

from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.selection_dialog import SelectionDialog
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog, alert_dialog
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import StarPilotPanel

# --- Map Data Definitions ---
MIDWEST_MAP = {"IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "MI": "Michigan", "MN": "Minnesota", "MO": "Missouri", "NE": "Nebraska", "ND": "North Dakota", "OH": "Ohio", "SD": "South Dakota", "WI": "Wisconsin"}
NORTHEAST_MAP = {"CT": "Connecticut", "ME": "Maine", "MA": "Massachusetts", "NH": "New Hampshire", "NJ": "New Jersey", "NY": "New York", "PA": "Pennsylvania", "RI": "Rhode Island", "VT": "Vermont"}
SOUTH_MAP = {"AL": "Alabama", "AR": "Arkansas", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "KY": "Kentucky", "LA": "Louisiana", "MD": "Maryland", "MS": "Mississippi", "NC": "North Carolina", "OK": "Oklahoma", "SC": "South Carolina", "TN": "Tennessee", "TX": "Texas", "VA": "Virginia", "WV": "West Virginia"}
WEST_MAP = {"AK": "Alaska", "AZ": "Arizona", "CA": "California", "CO": "Colorado", "HI": "Hawaii", "ID": "Idaho", "MT": "Montana", "NV": "Nevada", "NM": "New Mexico", "OR": "Oregon", "UT": "Utah", "WA": "Washington", "WY": "Wyoming"}
TERRITORIES_MAP = {"AS": "American Samoa", "GU": "Guam", "MP": "Northern Mariana Islands", "PR": "Puerto Rico", "VI": "Virgin Islands"}

AFRICA_MAP = {"DZ": "Algeria", "AO": "Angola", "BJ": "Benin", "BW": "Botswana", "BF": "Burkina Faso", "BI": "Burundi", "CM": "Cameroon", "CF": "Central African Republic", "TD": "Chad", "KM": "Comoros", "CG": "Congo (Brazzaville)", "CD": "Congo (Kinshasa)", "DJ": "Djibouti", "EG": "Egypt", "GQ": "Equatorial Guinea", "ER": "Eritrea", "ET": "Ethiopia", "GA": "Gabon", "GM": "Gambia", "GH": "Ghana", "GN": "Guinea", "GW": "Guinea-Bissau", "CI": "Ivory Coast", "KE": "Kenya", "LS": "Lesotho", "LR": "Liberia", "LY": "Libya", "MG": "Madagascar", "MW": "Malawi", "ML": "Mali", "MR": "Mauritania", "MA": "Morocco", "MZ": "Mozambique", "NA": "Namibia", "NE": "Niger", "NG": "Nigeria", "RW": "Rwanda", "SN": "Senegal", "SL": "Sierra Leone", "SO": "Somalia", "ZA": "South Africa", "SS": "South Sudan", "SD": "Sudan", "SZ": "Swaziland", "TZ": "Tanzania", "TG": "Togo", "TN": "Tunisia", "UG": "Uganda", "ZM": "Zambia", "ZW": "Zimbabwe"}
ANTARCTICA_MAP = {"AQ": "Antarctica"}
ASIA_MAP = {"AF": "Afghanistan", "AM": "Armenia", "AZ": "Azerbaijan", "BH": "Bahrain", "BD": "Bangladesh", "BT": "Bhutan", "BN": "Brunei", "KH": "Cambodia", "CN": "China", "CY": "Cyprus", "TL": "East Timor", "HK": "Hong Kong", "IN": "India", "ID": "Indonesia", "IR": "Iran", "IQ": "Iraq", "IL": "Israel", "JP": "Japan", "JO": "Jordan", "KZ": "Kazakhstan", "KW": "Kuwait", "KG": "Kyrgyzstan", "LA": "Laos", "LB": "Lebanon", "MY": "Malaysia", "MV": "Maldives", "MO": "Macao", "MN": "Mongolia", "MM": "Myanmar", "NP": "Nepal", "KP": "North Korea", "OM": "Oman", "PK": "Pakistan", "PS": "Palestine", "PH": "Philippines", "QA": "Qatar", "RU": "Russia", "SA": "Saudi Arabia", "SG": "Singapore", "KR": "South Korea", "LK": "Sri Lanka", "SY": "Syria", "TW": "Taiwan", "TJ": "Tajikistan", "TH": "Thailand", "TR": "Turkey", "TM": "Turkmenistan", "AE": "United Arab Emirates", "UZ": "Uzbekistan", "VN": "Vietnam", "YE": "Yemen"}
EUROPE_MAP = {"AL": "Albania", "AT": "Austria", "BY": "Belarus", "BE": "Belgium", "BA": "Bosnia and Herzegovina", "BG": "Bulgaria", "HR": "Croatia", "CZ": "Czech Republic", "DK": "Denmark", "EE": "Estonia", "FI": "Finland", "FR": "France", "GE": "Georgia", "DE": "Germany", "GR": "Greece", "HU": "Hungary", "IS": "Iceland", "IE": "Ireland", "IT": "Italy", "KZ": "Kazakhstan", "LV": "Latvia", "LT": "Lithuania", "LU": "Luxembourg", "MK": "Macedonia", "MD": "Moldova", "ME": "Montenegro", "NL": "Netherlands", "NO": "Norway", "PL": "Poland", "PT": "Portugal", "RO": "Romania", "RS": "Serbia", "SK": "Slovakia", "SI": "Slovenia", "ES": "Spain", "SE": "Sweden", "CH": "Switzerland", "TR": "Turkey", "UA": "Ukraine", "GB": "United Kingdom"}
NORTH_AMERICA_MAP = {"BS": "Bahamas", "BZ": "Belize", "CA": "Canada", "CR": "Costa Rica", "CU": "Cuba", "DO": "Dominican Republic", "SV": "El Salvador", "GL": "Greenland", "GD": "Grenada", "GT": "Guatemala", "HT": "Haiti", "HN": "Honduras", "JM": "Jamaica", "MX": "Mexico", "NI": "Nicaragua", "PA": "Panama", "TT": "Trinidad and Tobago", "US": "United States"}
OCEANIA_MAP = {"AU": "Australia", "FJ": "Fiji", "TF": "French Southern Territories", "NC": "New Caledonia", "NZ": "New Zealand", "PG": "Papua New Guinea", "SB": "Solomon Islands", "VU": "Vanuatu"}
SOUTH_AMERICA_MAP = {"AR": "Argentina", "BO": "Bolivia", "BR": "Brazil", "CL": "Chile", "CO": "Colombia", "EC": "Ecuador", "FK": "Falkland Islands", "GY": "Guyana", "PY": "Paraguay", "PE": "Peru", "SR": "Suriname", "UY": "Uruguay", "VE": "Venezuela"}


class StarPilotMapRegionLayout(StarPilotPanel):
  def __init__(self, region_map: dict[str, str]):
    super().__init__()
    self.CATEGORIES = []
    
    for key, name in sorted(region_map.items(), key=lambda item: item[1]):
      self.CATEGORIES.append({
        "title": name,
        "type": "toggle",
        "get_state": lambda k=key: self._get_map_state(k),
        "set_state": lambda s, k=key: self._set_map_state(k, s),
        "color": "#8CBF26"
      })
    self._rebuild_grid()

  def _get_map_state(self, key):
    selected_raw = self._params.get("MapsSelected", encoding='utf-8') or ""
    selected = [k.strip() for k in selected_raw.split(",") if k.strip()]
    return key in selected

  def _set_map_state(self, key, state):
    selected_raw = self._params.get("MapsSelected", encoding='utf-8') or ""
    selected = [k.strip() for k in selected_raw.split(",") if k.strip()]
    
    if state and key not in selected:
      selected.append(key)
    elif not state and key in selected:
      selected.remove(key)
      
    self._params.put("MapsSelected", ",".join(selected))


class StarPilotMapCountriesLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {"title": tr_noop("Africa"), "panel": "africa", "icon": "toggle_icons/icon_map.png", "color": "#8CBF26"},
      {"title": tr_noop("Antarctica"), "panel": "antarctica", "icon": "toggle_icons/icon_map.png", "color": "#8CBF26"},
      {"title": tr_noop("Asia"), "panel": "asia", "icon": "toggle_icons/icon_map.png", "color": "#8CBF26"},
      {"title": tr_noop("Europe"), "panel": "europe", "icon": "toggle_icons/icon_map.png", "color": "#8CBF26"},
      {"title": tr_noop("North America"), "panel": "north_america", "icon": "toggle_icons/icon_map.png", "color": "#8CBF26"},
      {"title": tr_noop("Oceania"), "panel": "oceania", "icon": "toggle_icons/icon_map.png", "color": "#8CBF26"},
      {"title": tr_noop("South America"), "panel": "south_america", "icon": "toggle_icons/icon_map.png", "color": "#8CBF26"},
    ]
    self._rebuild_grid()

class StarPilotMapStatesLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {"title": tr_noop("Midwest"), "panel": "midwest", "icon": "toggle_icons/icon_map.png", "color": "#8CBF26"},
      {"title": tr_noop("Northeast"), "panel": "northeast", "icon": "toggle_icons/icon_map.png", "color": "#8CBF26"},
      {"title": tr_noop("South"), "panel": "south", "icon": "toggle_icons/icon_map.png", "color": "#8CBF26"},
      {"title": tr_noop("West"), "panel": "west", "icon": "toggle_icons/icon_map.png", "color": "#8CBF26"},
      {"title": tr_noop("Territories"), "panel": "territories", "icon": "toggle_icons/icon_map.png", "color": "#8CBF26"},
    ]
    self._rebuild_grid()

class StarPilotMapsLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    
    self._sub_panels = {
      "countries": StarPilotMapCountriesLayout(),
      "states": StarPilotMapStatesLayout(),
      "africa": StarPilotMapRegionLayout(AFRICA_MAP),
      "antarctica": StarPilotMapRegionLayout(ANTARCTICA_MAP),
      "asia": StarPilotMapRegionLayout(ASIA_MAP),
      "europe": StarPilotMapRegionLayout(EUROPE_MAP),
      "north_america": StarPilotMapRegionLayout(NORTH_AMERICA_MAP),
      "oceania": StarPilotMapRegionLayout(OCEANIA_MAP),
      "south_america": StarPilotMapRegionLayout(SOUTH_AMERICA_MAP),
      "midwest": StarPilotMapRegionLayout(MIDWEST_MAP),
      "northeast": StarPilotMapRegionLayout(NORTHEAST_MAP),
      "south": StarPilotMapRegionLayout(SOUTH_MAP),
      "west": StarPilotMapRegionLayout(WEST_MAP),
      "territories": StarPilotMapRegionLayout(TERRITORIES_MAP),
    }

    self.CATEGORIES = [
      {"title": tr_noop("Download Maps"), "type": "hub", "on_click": self._on_download, "icon": "toggle_icons/icon_map.png", "color": "#8CBF26"},
      {"title": tr_noop("Auto Update Schedule"), "type": "value", "get_value": lambda: self._params.get("PreferredSchedule", encoding='utf-8') or "Manually", "on_click": self._on_schedule, "icon": "toggle_icons/icon_calendar.png", "color": "#8CBF26"},
      {"title": tr_noop("Countries"), "panel": "countries", "icon": "toggle_icons/icon_map.png", "color": "#8CBF26"},
      {"title": tr_noop("U.S. States"), "panel": "states", "icon": "toggle_icons/icon_map.png", "color": "#8CBF26"},
      {"title": tr_noop("Storage Used"), "type": "value", "get_value": self._get_storage, "on_click": lambda: None, "icon": "toggle_icons/icon_system.png", "color": "#8CBF26"},
      {"title": tr_noop("Remove Maps"), "type": "hub", "on_click": self._on_remove, "icon": "toggle_icons/icon_map.png", "color": "#8CBF26"},
    ]
    
    for name, panel in self._sub_panels.items():
      if hasattr(panel, 'set_navigate_callback'): panel.set_navigate_callback(self._navigate_to)
      if hasattr(panel, 'set_back_callback'): panel.set_back_callback(self._go_back)
      
    self._rebuild_grid()

  def _get_storage(self) -> str:
    maps_path = Path("/data/media/0/osm/offline")
    if not maps_path.exists():
      return "0 MB"
    total_size = sum(f.stat().st_size for f in maps_path.rglob('*') if f.is_file())
    mb = total_size / (1024 * 1024)
    if mb > 1024:
      return f"{(mb / 1024):.2f} GB"
    return f"{mb:.2f} MB"

  def _on_schedule(self):
    options = ["Manually", "Weekly", "Monthly"]
    current = self._params.get("PreferredSchedule", encoding='utf-8') or "Manually"
    def on_select(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put("PreferredSchedule", val)
        self._rebuild_grid()
    gui_app.set_modal_overlay(SelectionDialog(tr("Auto Update Schedule"), options, current, on_close=on_select))

  def _on_download(self):
    selected_raw = self._params.get("MapsSelected", encoding='utf-8') or ""
    selected = [k.strip() for k in selected_raw.split(",") if k.strip()]
    if not selected:
      gui_app.set_modal_overlay(alert_dialog(tr("Please select at least one region or state first!")))
      return
      
    def on_confirm(res):
      if res == DialogResult.CONFIRM:
        self._params_memory.put_bool("DownloadMaps", True)
        gui_app.set_modal_overlay(alert_dialog(tr("Map download started in background.")))
    
    gui_app.set_modal_overlay(ConfirmDialog(tr("Start downloading maps for selected regions?"), tr("Download"), on_close=on_confirm))

  def _on_remove(self):
    def on_confirm(res):
      if res == DialogResult.CONFIRM:
        maps_path = Path("/data/media/0/osm/offline")
        if maps_path.exists():
          shutil.rmtree(maps_path, ignore_errors=True)
        gui_app.set_modal_overlay(alert_dialog(tr("Maps removed.")))
        self._rebuild_grid()
    gui_app.set_modal_overlay(ConfirmDialog(tr("Delete all downloaded map data?"), tr("Remove"), on_close=on_confirm))
