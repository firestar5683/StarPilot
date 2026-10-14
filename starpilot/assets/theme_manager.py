#!/usr/bin/env python3
import glob
import io
import json
import os
import random
import requests
import shutil
import subprocess
import zipfile

from datetime import date, timedelta
from dateutil import easter
from pathlib import Path

from openpilot.starpilot.common.starpilot_download_utilities import HF_BUCKET, GITHUB_URL, download_file, get_resource_urls, handle_error, verify_download
from openpilot.starpilot.common.theme_asset_names import find_matching_theme_asset_file, find_matching_theme_asset_name
from openpilot.starpilot.common.starpilot_utilities import delete_file, extract_zip, load_json_file, update_json_file
from openpilot.starpilot.common.starpilot_variables import ACTIVE_THEME_PATH, RANDOM_EVENTS_PATH, RESOURCES_REPO, THEME_SAVE_PATH

CANCEL_DOWNLOAD_PARAM = "CancelThemeDownload"
DOWNLOAD_PROGRESS_PARAM = "ThemeDownloadProgress"

HOLIDAY_THEME_PATH = Path(__file__).parent / "holiday_themes"
STOCKOP_THEME_PATH = Path(__file__).parent / "stock_theme"
LOCAL_RESOURCES_PATH = Path(os.getenv("STARPILOT_LOCAL_RESOURCES_PATH", "~/StarPilot-Resources")).expanduser()

HOLIDAY_SLUGS = {
  "new_years": "New Year's",
  "valentines_day": "Valentine's Day",
  "st_patricks_day": "St. Patrick's Day",
  "world_frog_day": "World Frog Day",
  "april_fools": "April Fools",
  "easter_week": "Easter",
  "may_the_fourth": "May the Fourth",
  "cinco_de_mayo": "Cinco de Mayo",
  "stitch_day": "Stitch Day",
  "fourth_of_july": "Fourth of July",
  "halloween_week": "Halloween",
  "thanksgiving_week": "Thanksgiving",
  "christmas_week": "Christmas"
}

THEME_COMPONENT_PARAMS = {
  "boot_logos": "BootLogoToDownload",
  "colors": "ColorToDownload",
  "distance_icons": "DistanceIconToDownload",
  "icons": "IconToDownload",
  "signals": "SignalToDownload",
  "sounds": "SoundToDownload",
  "steering_wheels": "WheelToDownload"
}

class ThemeManager:
  def __init__(self, params, params_memory, boot_run=False):
    self.params = params
    self.params_memory = params_memory

    self.downloading_theme = False
    self.theme_updated = False

    self.holiday_theme = "stock"

    self.previous_asset_mappings = {}

    self.theme_sizes_path = THEME_SAVE_PATH / "theme_sizes.json"

    # Ensure theme storage layout exists on desktop and device alike.
    (THEME_SAVE_PATH / "bootlogos").mkdir(parents=True, exist_ok=True)
    (THEME_SAVE_PATH / "theme_packs").mkdir(parents=True, exist_ok=True)
    (THEME_SAVE_PATH / "steering_wheels").mkdir(parents=True, exist_ok=True)
    self.sync_local_resources()

    self.theme_sizes = load_json_file(self.theme_sizes_path)

    self.session = requests.Session()
    self.session.headers.update({
      "Accept": "application/vnd.github.v3+json",
      "Accept-Language": "en",
      "User-Agent": "starpilot-theme-downloader/1.0 (https://github.com/FrogAi/StarPilot)"
    })

    if boot_run:
      self.copy_default_theme()

  @staticmethod
  def _local_resources_available():
    return LOCAL_RESOURCES_PATH.is_dir() and (LOCAL_RESOURCES_PATH / ".git").exists()

  @staticmethod
  def _git_list_tree(ref):
    result = subprocess.run(
      ["git", "-C", str(LOCAL_RESOURCES_PATH), "ls-tree", "-r", "--name-only", ref],
      capture_output=True,
      text=True,
      check=True,
    )
    return [line for line in result.stdout.splitlines() if line]

  @staticmethod
  def _git_show_bytes(ref, path):
    result = subprocess.run(
      ["git", "-C", str(LOCAL_RESOURCES_PATH), "show", f"{ref}:{path}"],
      capture_output=True,
      check=True,
    )
    return result.stdout

  @staticmethod
  def _directory_has_files(path):
    return path.is_dir() and any(path.iterdir())

  @staticmethod
  def _write_file_if_missing(destination, data):
    if destination.exists() and destination.stat().st_size > 0:
      return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return True

  @staticmethod
  def _extract_zip_if_missing(zip_bytes, destination):
    if ThemeManager._directory_has_files(destination):
      return False
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
      archive.extractall(destination)
    return True

  def sync_local_resources(self):
    if not self._local_resources_available():
      return

    try:
      imported_assets = 0

      for path in self._git_list_tree("Steering-Wheels"):
        suffix = Path(path).suffix.lower()
        if suffix not in {".gif", ".png", ".webp", ".jpg", ".jpeg"}:
          continue
        destination = THEME_SAVE_PATH / "steering_wheels" / Path(path).name
        imported_assets += int(self._write_file_if_missing(destination, self._git_show_bytes("Steering-Wheels", path)))

      for path in self._git_list_tree("Themes"):
        path_obj = Path(path)
        suffix = path_obj.suffix.lower()

        if path_obj.parts[:1] == ("bootlogo",) and suffix in {".png", ".jpg", ".jpeg"}:
          destination = THEME_SAVE_PATH / "bootlogos" / path_obj.name
          imported_assets += int(self._write_file_if_missing(destination, self._git_show_bytes("Themes", path)))
          continue

        if suffix != ".zip" or len(path_obj.parts) != 2:
          continue

        theme_name, archive_name = path_obj.parts
        component = Path(archive_name).stem.lower()
        if component not in {"colors", "distance_icons", "icons", "signals", "sounds"}:
          continue

        destination = THEME_SAVE_PATH / "theme_packs" / theme_name / component
        imported_assets += int(self._extract_zip_if_missing(self._git_show_bytes("Themes", path), destination))

      for path in self._git_list_tree("Distance-Icons"):
        path_obj = Path(path)
        if path_obj.suffix.lower() != ".zip":
          continue
        destination = THEME_SAVE_PATH / "theme_packs" / path_obj.stem / "distance_icons"
        imported_assets += int(self._extract_zip_if_missing(self._git_show_bytes("Distance-Icons", path), destination))

      if imported_assets:
        print(f"Imported {imported_assets} local theme assets from {LOCAL_RESOURCES_PATH}")
    except (FileNotFoundError, subprocess.CalledProcessError, zipfile.BadZipFile, OSError) as error:
      print(f"Failed to sync local theme resources from {LOCAL_RESOURCES_PATH}: {error}")

  @staticmethod
  def calculate_thanksgiving(year):
    november_first = date(year, 11, 1)
    days_to_thursday = (3 - november_first.weekday()) % 7
    first_thursday = november_first + timedelta(days=days_to_thursday)
    return first_thursday + timedelta(days=21)

  @staticmethod
  def copy_default_theme():
    world_frog_day_theme_path = HOLIDAY_THEME_PATH / "world_frog_day"

    for theme_subfolder_name, save_subfolder_path in [
      ("colors", "theme_packs/frog/colors"),
      ("distance_icons", "theme_packs/frog-animated/distance_icons"),
      ("icons", "theme_packs/frog-animated/icons"),
      ("signals", "theme_packs/frog/signals"),
      ("sounds", "theme_packs/frog/sounds"),
    ]:
      source_folder_path = world_frog_day_theme_path / theme_subfolder_name
      destination_folder_path = THEME_SAVE_PATH / save_subfolder_path
      destination_folder_path.mkdir(parents=True, exist_ok=True)
      shutil.copytree(source_folder_path, destination_folder_path, dirs_exist_ok=True)

    steering_wheel_image_path = world_frog_day_theme_path / "steering_wheel/wheel.png"
    steering_wheel_save_path = THEME_SAVE_PATH / "steering_wheels/frog.png"
    steering_wheel_save_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(steering_wheel_image_path, steering_wheel_save_path)

    default_boot_logo_path = Path(__file__).parent / "other_images/starpilot_boot_logo.jpg"
    boot_logo_save_path = THEME_SAVE_PATH / "bootlogos/starpilot.jpg"
    boot_logo_save_path.parent.mkdir(parents=True, exist_ok=True)
    if default_boot_logo_path.exists():
      should_refresh_default_boot_logo = not boot_logo_save_path.exists()
      if not should_refresh_default_boot_logo:
        try:
          should_refresh_default_boot_logo = default_boot_logo_path.read_bytes() != boot_logo_save_path.read_bytes()
        except OSError:
          should_refresh_default_boot_logo = True

      if should_refresh_default_boot_logo:
        shutil.copy2(default_boot_logo_path, boot_logo_save_path)

  def download_theme(self, theme_component, theme_name, asset_param, starpilot_toggles):
    self.downloading_theme = True

    resource_urls = get_resource_urls(self.session)
    if not resource_urls:
      handle_error(None, asset_param, "Repository unavailable", "Hugging Face and GitHub are offline...", self.params_memory, DOWNLOAD_PROGRESS_PARAM)
      self.downloading_theme = False
      return

    if theme_component == "boot_logos":
      download_path = THEME_SAVE_PATH / "bootlogos" / theme_name
      extensions = [".png", ".jpg", ".jpeg"]
      name_candidates = list(dict.fromkeys([theme_name, theme_name.replace("_", "-"), theme_name.replace("-", "_")]))
    elif theme_component == "distance_icons":
      download_path = THEME_SAVE_PATH / "theme_packs" / theme_name / theme_component
      extensions = [".zip"]
      name_candidates = [theme_name]
    elif theme_component == "steering_wheels":
      download_path = THEME_SAVE_PATH / theme_component / theme_name
      extensions = [".gif", ".png"]
      name_candidates = [theme_name]
    else:
      download_path = THEME_SAVE_PATH / "theme_packs" / theme_name / theme_component
      extensions = [".zip"]
      name_candidates = [theme_name]

    for extension in extensions:
      theme_urls = []
      for resource_url in resource_urls:
        source_prefix = f"{resource_url}/theme" if "huggingface.co/buckets/" in resource_url else resource_url
        if theme_component == "boot_logos":
          path_prefix = f"{source_prefix}/Themes/bootlogo"
          theme_urls.extend(f"{path_prefix}/{candidate}{extension}" for candidate in name_candidates)
        elif theme_component == "distance_icons":
          theme_urls.append(f"{source_prefix}/Distance-Icons/{theme_name}{extension}")
        elif theme_component == "steering_wheels":
          theme_urls.append(f"{source_prefix}/Steering-Wheels/{theme_name}{extension}")
        else:
          theme_urls.append(f"{source_prefix}/Themes/{theme_name}/{theme_component}{extension}")

      for theme_url in theme_urls:
        theme_path = download_path.with_suffix(extension)
        delete_file(theme_path)

        source = "Hugging Face" if "huggingface.co/buckets/" in theme_url else "GitHub"
        print(f"Downloading theme from {source}: {theme_name}")
        downloaded_path = download_file(CANCEL_DOWNLOAD_PARAM, theme_path, asset_param, self.params_memory, DOWNLOAD_PROGRESS_PARAM, self.session, theme_url)
        theme_path = downloaded_path or theme_path

        if self.params_memory.get_bool(CANCEL_DOWNLOAD_PARAM):
          delete_file(theme_path)
          handle_error(None, asset_param, "Download cancelled...", "Download cancelled...", self.params_memory, DOWNLOAD_PROGRESS_PARAM)

          self.downloading_theme = False
          return

        if verify_download(theme_path, self.params_memory, self.session, theme_url):
          print(f"Theme {theme_name} downloaded and verified successfully from {source}!")
          self.update_theme_size(theme_component, theme_name, theme_path.stat().st_size)

          if extension == ".zip":
            self.params_memory.put(DOWNLOAD_PROGRESS_PARAM, "Unpacking theme...")
            extract_zip(theme_path, download_path)

          self.params_memory.put(DOWNLOAD_PROGRESS_PARAM, "Downloaded!")
          self.params_memory.remove(asset_param)

          self.downloading_theme = False

          self.update_themes(starpilot_toggles, update_assets=False)
          return

    handle_error(download_path, asset_param, "Download failed...", "Download failed...", self.params_memory, DOWNLOAD_PROGRESS_PARAM)
    self.downloading_theme = False

  def fetch_assets(self, repo_url, starpilot_toggles, *, update_assets=True):
    is_github = "github" in repo_url
    is_huggingface = "huggingface.co/buckets/" in repo_url

    assets = {"boot_logos": [], "themes": {}, "wheels": []}
    try:
      def list_files(branch):
        if is_huggingface:
          response = self.session.get(f"https://huggingface.co/api/buckets/{HF_BUCKET}/tree/theme/{branch}?recursive=true", timeout=10)
          response.raise_for_status()
          prefix = {
            "Themes": "theme/Themes/",
            "Distance-Icons": "theme/Distance-Icons/",
            "Steering-Wheels": "theme/Steering-Wheels/",
          }[branch]
          return [
            {
              "path": item.get("path", "")[len(prefix):],
              "name": Path(item.get("path", "")).name,
              "type": item.get("type"),
              "size": item.get("size", 0),
            }
            for item in response.json()
            if item.get("type") == "file" and item.get("path", "").startswith(prefix)
          ]
        if is_github:
          response = self.session.get(f"https://api.github.com/repos/{RESOURCES_REPO}/git/trees/{branch}?recursive=1", timeout=10)
          response.raise_for_status()
          return [
            {
              "path": item.get("path", ""),
              "name": Path(item.get("path", "")).name,
              "type": item.get("type"),
              "size": item.get("size", 0),
            }
            for item in response.json().get("tree", [])
            if item.get("type") == "blob"
          ]
        print(f"Unsupported repository URL: {repo_url}")
        return []

      def file_size(branch, path, fallback):
        if is_github or is_huggingface:
          return int(fallback or 0)

      for branch in ["Distance-Icons", "Steering-Wheels"]:
        for item in list_files(branch):
          if item.get("type") not in ("file", "blob"):
            continue

          path = item["path"]
          size = file_size(branch, path, item.get("size", 0))

          if branch == "Steering-Wheels":
            assets["wheels"].append(path)
            theme_name = Path(path).stem
            local_files = list((THEME_SAVE_PATH / "steering_wheels").glob(f"{theme_name}.*"))
            if update_assets and local_files and size > 0:
              local_size = self.theme_sizes.get("wheels", {}).get(theme_name)
              if local_size != size:
                self.download_theme("steering_wheels", theme_name, THEME_COMPONENT_PARAMS["steering_wheels"], starpilot_toggles)

          elif branch == "Distance-Icons":
            component_name = "distance_icons"
            theme_name = Path(path).stem
            assets["themes"].setdefault(theme_name, set()).add(component_name)

            local_path = THEME_SAVE_PATH / "theme_packs" / theme_name / component_name
            if update_assets and local_path.exists() and size > 0:
              local_size = self.theme_sizes.get("themes", {}).get(theme_name, {}).get(component_name)
              if local_size != size:
                self.download_theme(component_name, theme_name, THEME_COMPONENT_PARAMS[component_name], starpilot_toggles)

      branch = "Themes"
      for item in list_files(branch):
        if item.get("type") not in ("file", "blob") or "/" not in item["path"]:
          continue

        expected_size = file_size(branch, item["path"], item.get("size", 0))

        theme_name, sub_path = item["path"].split("/", 1)
        theme_path = sub_path.lower()

        if theme_name.lower() == "bootlogo":
          if Path(sub_path).suffix.lower() not in (".png", ".jpg", ".jpeg"):
            continue

          assets["boot_logos"].append(sub_path)
          logo_name = Path(sub_path).stem
          local_files = list((THEME_SAVE_PATH / "bootlogos").glob(f"{logo_name}.*"))
          if update_assets and local_files and expected_size > 0:
            local_size = self.theme_sizes.get("boot_logos", {}).get(logo_name)
            if local_size != expected_size:
              print(f"boot logo {logo_name} is outdated, redownloading...")
              self.download_theme("boot_logos", logo_name, THEME_COMPONENT_PARAMS["boot_logos"], starpilot_toggles)
          continue

        for key in ("colors", "icons", "signals", "sounds"):
          if key in theme_path:
            assets["themes"].setdefault(theme_name, set()).add(key)

            local_path = THEME_SAVE_PATH / "theme_packs" / theme_name / key
            if update_assets and local_path.exists():
              local_size = self.theme_sizes.get("themes", {}).get(theme_name, {}).get(key)
              if local_size != expected_size:
                print(f"{key} {theme_name} is outdated, redownloading...")
                self.download_theme(key, theme_name, THEME_COMPONENT_PARAMS[key], starpilot_toggles)
            break

      assets["boot_logos"].sort()
      assets["themes"] = {key: sorted(list(value)) for key, value in assets["themes"].items()}
      assets["wheels"].sort()
      return assets

    except requests.exceptions.RequestException as error:
      source = "Hugging Face" if is_huggingface else "GitHub"
      print(f"Failed to fetch theme sizes from {source}: {error}")
      return {}

  @staticmethod
  def format_name(name, component):
    base = Path(name).stem
    creator = ""
    if "~" in base:
      base, creator = base.split("~", 1)

    parts = base.replace("_", " ").replace("-", " ").split()
    display = " ".join(part.capitalize() for part in parts)

    if creator:
      return f"{display} - by: {creator}"
    return display

  @staticmethod
  def get_full_themes():
    theme_packs_path = THEME_SAVE_PATH / "theme_packs"
    if not theme_packs_path.exists():
      return []

    valid_themes = set()
    for theme_directory in theme_packs_path.iterdir():
      if not theme_directory.is_dir():
        continue

      base_name = theme_directory.name.replace("-animated", "")

      animated_path = theme_packs_path / f"{base_name}-animated"
      base_path = theme_packs_path / base_name

      base_valid = all((base_path / asset).is_dir() for asset in {"colors", "sounds"})
      animated_icons_exist = (animated_path / "icons").is_dir()
      base_icons_exist = (base_path / "icons").is_dir()

      if base_valid and (animated_icons_exist or base_icons_exist):
        if animated_icons_exist:
          valid_themes.add(f"{base_name}-animated")
        else:
          valid_themes.add(base_name)

    return sorted(valid_themes)

  @staticmethod
  def get_holiday_theme_dates(year):
    return {
      "new_years": date(year, 1, 1),
      "valentines_day": date(year, 2, 14),
      "st_patricks_day": date(year, 3, 17),
      "world_frog_day": date(year, 3, 20),
      "april_fools": date(year, 4, 1),
      "easter_week": easter.easter(year),
      "may_the_fourth": date(year, 5, 4),
      "cinco_de_mayo": date(year, 5, 5),
      "stitch_day": date(year, 6, 26),
      "fourth_of_july": date(year, 7, 4),
      "halloween_week": date(year, 10, 31),
      "thanksgiving_week": ThemeManager.calculate_thanksgiving(year),
      "christmas_week": date(year, 12, 25)
    }

  def handle_verification_failure(self, extension, theme_component, theme_name, asset_param, theme_path, download_path, starpilot_toggles, fallback_url=GITHUB_URL):
    source = "GitHub"

    if theme_component == "boot_logos":
      download_link = f"{fallback_url}/Themes/bootlogo"
      name_candidates = list(dict.fromkeys([theme_name, theme_name.replace("_", "-"), theme_name.replace("-", "_")]))
    elif theme_component == "distance_icons":
      download_link = f"{fallback_url}/Distance-Icons/{theme_name}"
      name_candidates = [theme_name]
    elif theme_component == "steering_wheels":
      download_link = f"{fallback_url}/Steering-Wheels/{theme_name}"
      name_candidates = [theme_name]
    else:
      download_link = f"{fallback_url}/Themes/{theme_name}/{theme_component}"
      name_candidates = [theme_name]

    for candidate in name_candidates:
      delete_file(theme_path)

      theme_url = f"{download_link}/{candidate}{extension}" if theme_component == "boot_logos" else download_link + extension
      print(f"Downloading theme from {source}: {theme_name}")
      download_file(CANCEL_DOWNLOAD_PARAM, theme_path, asset_param, self.params_memory, DOWNLOAD_PROGRESS_PARAM, self.session, theme_url)

      if verify_download(theme_path, self.params_memory, self.session, theme_url):
        print(f"Theme {theme_name} downloaded and verified successfully from {source}!")
        self.update_theme_size(theme_component, theme_name, theme_path.stat().st_size)

        if extension == ".zip":
          self.params_memory.put(DOWNLOAD_PROGRESS_PARAM, "Unpacking theme...")
          extract_zip(theme_path, download_path)

        self.params_memory.put(DOWNLOAD_PROGRESS_PARAM, "Downloaded!")
        self.params_memory.remove(asset_param)

        self.downloading_theme = False

        self.update_themes(starpilot_toggles)
        return True

    return False

  @staticmethod
  def is_within_week_of(target_date, current_date):
    start_of_week = target_date - timedelta(days=target_date.weekday())
    return start_of_week <= current_date < target_date

  @staticmethod
  def randomize_distance_icons(available_themes, selected_theme):
    theme_packs_path = THEME_SAVE_PATH / "theme_packs"
    if not theme_packs_path.exists():
      return "stock"

    candidates = []
    for theme_pack in theme_packs_path.iterdir():
      if not theme_pack.is_dir():
        continue

      distance_icons_dir = theme_pack / "distance_icons"
      if not distance_icons_dir.is_dir():
        continue

      icon_name = theme_pack.name.lower()

      theme_association = [theme for theme in available_themes if theme.replace("-animated", "") in icon_name]
      if theme_association and selected_theme not in icon_name:
        continue

      weight = 5 if selected_theme in icon_name else 1
      candidates.extend([theme_pack.name] * weight)

    return random.choice(candidates) if candidates else "stock"

  @staticmethod
  def randomize_theme_asset(available_themes):
    if not available_themes:
      return "stock"

    return random.choice(available_themes)

  @staticmethod
  def randomize_wheel_image(available_themes, selected_theme):
    steering_wheels_path = THEME_SAVE_PATH / "steering_wheels"
    if not steering_wheels_path.exists():
      return "stock"

    candidates = []
    for wheel_file in steering_wheels_path.iterdir():
      if not wheel_file.is_file():
        continue

      name = wheel_file.stem.lower()

      theme_association = [theme for theme in available_themes if theme.replace("-animated", "") in name]
      if theme_association and selected_theme not in name:
        continue

      weight = 5 if selected_theme in name else 1
      candidates.extend([wheel_file.stem] * weight)

    return random.choice(candidates) if candidates else "stock"

  def update_active_theme(self, time_validated, starpilot_toggles, boot_run=False, randomize_theme=False):
    boot_logo = getattr(starpilot_toggles, "boot_logo", "starpilot")

    if time_validated and starpilot_toggles.holiday_themes:
      self.holiday_theme = self.update_holiday()
    else:
      self.holiday_theme = "stock"

    if self.holiday_theme != "stock":
      asset_mappings = {
        "boot_logo": ("boot_logo", boot_logo),
        "color_scheme": ("colors", self.holiday_theme),
        "distance_icons": ("distance_icons", self.holiday_theme),
        "icon_pack": ("icons", self.holiday_theme),
        "sound_pack": ("sounds", self.holiday_theme),
        "turn_signal_pack": ("signals", self.holiday_theme),
        "wheel_image": ("wheel_image", self.holiday_theme)
      }
    elif (boot_run or randomize_theme) and starpilot_toggles.random_themes:
      available_themes = self.get_full_themes()

      if starpilot_toggles.random_themes_holidays:
        available_themes.extend(HOLIDAY_SLUGS.keys())

      selected_theme = self.randomize_theme_asset(available_themes)

      asset_mappings = {
        "boot_logo": ("boot_logo", boot_logo),
        "color_scheme": ("colors", selected_theme.replace("-animated", "")),
        "distance_icons": ("distance_icons", self.randomize_distance_icons(available_themes, selected_theme.replace("-animated", ""))),
        "icon_pack": ("icons", selected_theme),
        "sound_pack": ("sounds", selected_theme.replace("-animated", "")),
        "turn_signal_pack": ("signals", selected_theme.replace("-animated", "")),
        "wheel_image": ("wheel_image", self.randomize_wheel_image(available_themes, selected_theme.replace("-animated", "")))
      }
    elif not starpilot_toggles.random_themes:
      asset_mappings = {
        "boot_logo": ("boot_logo", boot_logo),
        "color_scheme": ("colors", starpilot_toggles.color_scheme),
        "distance_icons": ("distance_icons", starpilot_toggles.distance_icons),
        "icon_pack": ("icons", starpilot_toggles.icon_pack),
        "sound_pack": ("sounds", starpilot_toggles.sound_pack),
        "turn_signal_pack": ("signals", starpilot_toggles.signal_icons),
        "wheel_image": ("wheel_image", starpilot_toggles.wheel_image)
      }
    else:
      return

    if asset_mappings != self.previous_asset_mappings:
      for asset, (asset_type, current_value) in asset_mappings.items():
        print(f"Updating {asset}: {asset_type} with value {current_value}")

        if asset_type == "boot_logo":
          self.update_boot_logo(current_value)
        elif asset_type == "wheel_image":
          self.update_wheel_image(current_value, boot_run=boot_run)
        else:
          self.update_theme_asset(asset_type, current_value, boot_run=boot_run)

      self.previous_asset_mappings = asset_mappings

      self.theme_updated = True

  def update_holiday(self):
    current_date = date.today()

    holidays = self.get_holiday_theme_dates(current_date.year)
    for holiday, holiday_date in holidays.items():
      if (holiday.endswith("_week") and self.is_within_week_of(holiday_date, current_date)) or (current_date == holiday_date):
        return holiday

    return "stock"

  def update_theme_asset(self, asset_type, theme, boot_run=False):
    save_location = ACTIVE_THEME_PATH / asset_type

    if self.holiday_theme != "stock":
      asset_location = HOLIDAY_THEME_PATH / self.holiday_theme / asset_type
    elif theme in HOLIDAY_SLUGS:
      asset_location = HOLIDAY_THEME_PATH / theme / asset_type
    elif f"{theme}_week" in HOLIDAY_SLUGS:
      asset_location = HOLIDAY_THEME_PATH / f"{theme}_week" / asset_type
    else:
      asset_location = THEME_SAVE_PATH / "theme_packs" / theme / asset_type

    if not asset_location.exists() or theme == "stock":
      asset_location = STOCKOP_THEME_PATH / asset_type
      print(f"Using the stock {asset_type[:-1]} instead")

    delete_file(save_location, print_error=not boot_run)

    save_location.parent.mkdir(parents=True, exist_ok=True)
    save_location.symlink_to(asset_location, target_is_directory=True)
    print(f"Linked {save_location} to {asset_location}")

  def update_theme_params(self, downloadable_boot_logos, downloadable_colors, downloadable_distance_icons, downloadable_icons, downloadable_signals, downloadable_sounds, downloadable_wheels):
    boot_logos_dir = THEME_SAVE_PATH / "bootlogos"
    theme_packs_dir = THEME_SAVE_PATH / "theme_packs"
    steering_wheels_dir = THEME_SAVE_PATH / "steering_wheels"
    boot_logos_dir.mkdir(parents=True, exist_ok=True)
    theme_packs_dir.mkdir(parents=True, exist_ok=True)
    steering_wheels_dir.mkdir(parents=True, exist_ok=True)

    def update_param(key, assets, subfolder):
      if subfolder == "boot_logos":
        existing_assets = {item.stem.lower() for item in boot_logos_dir.glob("*") if item.is_file()}
        pending_assets = [asset for asset in assets if asset.lower() not in existing_assets]
        self.params.put(key, ",".join(sorted(set(pending_assets))))
        print(f"{key} updated successfully")
        return
      if subfolder == "steering_wheels":
        themes_path = steering_wheels_dir
        existing_assets = {self.format_name(item.name, "steering_wheels") for item in themes_path.glob("*") if item.is_file()}
      else:
        themes_path = theme_packs_dir
        existing_assets = {self.format_name(item.parent.name, subfolder) for item in themes_path.glob(f"*/{subfolder}") if item.is_dir()}

      self.params.put(key, ",".join(sorted(set(assets) - existing_assets)))
      print(f"{key} updated successfully")

    update_param("DownloadableBootLogos", downloadable_boot_logos, "boot_logos")
    update_param("DownloadableColors", downloadable_colors, "colors")
    update_param("DownloadableDistanceIcons", downloadable_distance_icons, "distance_icons")
    update_param("DownloadableIcons", downloadable_icons, "icons")
    update_param("DownloadableSignals", downloadable_signals, "signals")
    update_param("DownloadableSounds", downloadable_sounds, "sounds")
    update_param("DownloadableWheels", downloadable_wheels, "steering_wheels")

    downloaded_themes = {}
    for theme_dir in theme_packs_dir.iterdir():
      components = []
      for component in ["colors", "distance_icons", "icons", "signals", "sounds"]:
        if (theme_dir / component).is_dir():
          components.append(component)

      if components:
        theme_name = self.format_name(theme_dir.name, "theme_packs")
        downloaded_themes[theme_name] = sorted(components)

    downloaded_boot_logos = []
    for boot_logo_file in boot_logos_dir.iterdir():
      if boot_logo_file.is_file():
        downloaded_boot_logos.append(self.format_name(boot_logo_file.name, "boot_logos"))

    downloaded_wheels = []
    for wheel_file in steering_wheels_dir.iterdir():
      if wheel_file.is_file():
        downloaded_wheels.append(self.format_name(wheel_file.name, "steering_wheels"))

    self.params.put("ThemesDownloaded", {
      "boot_logos": sorted(downloaded_boot_logos),
      "themes": {key: downloaded_themes[key] for key in sorted(downloaded_themes)},
      "steering_wheels": sorted(downloaded_wheels)
    })

    print("ThemesDownloaded updated successfully")

  def update_theme_size(self, theme_component, theme_name, file_size):
    if theme_component == "boot_logos":
      key = "boot_logos"
    elif theme_component == "steering_wheels":
      key = "wheels"
    else:
      key = "themes"

    if key not in self.theme_sizes:
      self.theme_sizes[key] = {}

    if key in {"boot_logos", "wheels"}:
      self.theme_sizes[key][theme_name] = file_size
    else:
      if theme_name not in self.theme_sizes[key]:
        self.theme_sizes[key][theme_name] = {}
      self.theme_sizes[key][theme_name][theme_component] = file_size

    update_json_file(self.theme_sizes_path, self.theme_sizes)

  def update_themes(self, starpilot_toggles, boot_run=False, *, update_assets=True):
    if self.downloading_theme:
      return

    self.sync_local_resources()

    resource_urls = get_resource_urls(self.session)
    if not resource_urls:
      print("Hugging Face and GitHub are offline...")
      self.update_theme_params([], [], [], [], [], [], [])
      return

    assets = {}
    for repo_url in resource_urls:
      assets = self.fetch_assets(repo_url, starpilot_toggles, update_assets=update_assets)
      if assets:
        break
    if not assets:
      return

    downloadable_boot_logos = []
    downloadable_colors = []
    downloadable_distance_icons = []
    downloadable_icons = []
    downloadable_signals = []
    downloadable_sounds = []

    for theme, available_assets in assets["themes"].items():
      theme_name = self.format_name(theme, "theme_packs")
      print(f"Theme found: {theme_name}")

      if "colors" in available_assets:
        downloadable_colors.append(theme_name)
      if "distance_icons" in available_assets:
        downloadable_distance_icons.append(theme_name)
      if "icons" in available_assets:
        downloadable_icons.append(theme_name)
      if "signals" in available_assets:
        downloadable_signals.append(theme_name)
      if "sounds" in available_assets:
        downloadable_sounds.append(theme_name)

    downloadable_boot_logos = [Path(boot_logo).stem for boot_logo in assets["boot_logos"]]
    downloadable_wheels = [self.format_name(wheel, "steering_wheels") for wheel in assets["wheels"]]

    print(f"Downloadable Boot Logos: {downloadable_boot_logos}")
    print(f"Downloadable Colors: {downloadable_colors}")
    print(f"Downloadable Icons: {downloadable_icons}")
    print(f"Downloadable Signals: {downloadable_signals}")
    print(f"Downloadable Sounds: {downloadable_sounds}")
    print(f"Downloadable Distance Icons: {downloadable_distance_icons}")
    print(f"Downloadable Wheels: {downloadable_wheels}")

    if boot_run and update_assets:
      self.validate_themes(downloadable_boot_logos, downloadable_colors, downloadable_distance_icons, downloadable_icons, downloadable_signals, downloadable_sounds, downloadable_wheels, starpilot_toggles)

    self.update_theme_params(downloadable_boot_logos, downloadable_colors, downloadable_distance_icons, downloadable_icons, downloadable_signals, downloadable_sounds, downloadable_wheels)

  @staticmethod
  def update_boot_logo(image):
    default_boot_logo = Path(__file__).parent / "other_images/starpilot_boot_logo.jpg"

    if not default_boot_logo.exists():
      return

    source_file = find_matching_theme_asset_file(THEME_SAVE_PATH / "bootlogos", image) or default_boot_logo

    if source_file.resolve() == default_boot_logo.resolve():
      print(f"Boot logo unchanged: {default_boot_logo}")
      return

    shutil.copy2(source_file, default_boot_logo)
    print(f"Copied {source_file} to {default_boot_logo}")

  def update_wheel_image(self, image, boot_run=False, random_event=False):
    wheel_save_location = ACTIVE_THEME_PATH / "steering_wheel"

    if self.holiday_theme != "stock":
      wheel_location = HOLIDAY_THEME_PATH / self.holiday_theme / "steering_wheel"
    elif random_event:
      wheel_location = RANDOM_EVENTS_PATH / "steering_wheels"
    elif image == "stock":
      wheel_location = STOCKOP_THEME_PATH / "steering_wheel"
    elif image in HOLIDAY_SLUGS:
      wheel_location = HOLIDAY_THEME_PATH / image / "steering_wheel"
    elif f"{image}_week" in HOLIDAY_SLUGS:
      wheel_location = HOLIDAY_THEME_PATH / f"{image}_week" / "steering_wheel"
    else:
      wheel_location = THEME_SAVE_PATH / "steering_wheels"

    if not wheel_location.exists():
      wheel_location = STOCKOP_THEME_PATH / "steering_wheel"
      print("Using the stock steering wheel instead")

    delete_file(wheel_save_location, print_error=not boot_run)
    wheel_save_location.mkdir(parents=True, exist_ok=True)

    image_name = image.replace(" ", "_").lower()
    matching_files = [images for images in wheel_location.iterdir() if images.stem.lower() in {image_name, "wheel"}]
    if not matching_files:
      stock_location = STOCKOP_THEME_PATH / "steering_wheel"
      matching_files = [images for images in stock_location.iterdir() if images.stem.lower() == "wheel"]
      if matching_files:
        print(f"Steering wheel '{image}' not found, using the stock steering wheel instead")

    if not matching_files:
      print(f"No steering wheel asset found for '{image}'")
      return

    source_file = matching_files[0]
    destination_file = wheel_save_location / f"wheel{source_file.suffix}"
    destination_file.symlink_to(source_file)
    print(f"Linked {destination_file} to {source_file}")

  def validate_themes(self, downloadable_boot_logos, downloadable_colors, downloadable_distance_icons, downloadable_icons, downloadable_signals, downloadable_sounds, downloadable_wheels, starpilot_toggles):
    downloaded_data = self.params.get("ThemesDownloaded")
    if isinstance(downloaded_data, (bytes, bytearray)):
      downloaded_data = downloaded_data.decode("utf-8", "ignore")
    if isinstance(downloaded_data, str):
      try:
        downloaded_data = json.loads(downloaded_data)
      except json.JSONDecodeError:
        downloaded_data = {}
    if not isinstance(downloaded_data, dict):
      downloaded_data = {}

    boot_logos_path = THEME_SAVE_PATH / "bootlogos"
    for display_name in downloaded_data.get("boot_logos", []):
      if not find_matching_theme_asset_file(boot_logos_path, display_name):
        file_stem = find_matching_theme_asset_name(downloadable_boot_logos, display_name) or display_name.replace(" ", "_").lower()
        print(f"Missing boot logo '{display_name}'. Downloading...")
        self.download_theme("boot_logos", file_stem, THEME_COMPONENT_PARAMS["boot_logos"], starpilot_toggles)
        self.update_active_theme(True, starpilot_toggles)

    for display_name, components in downloaded_data.get("themes", {}).items():
      raw_name = display_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
      theme_folder_name = raw_name.replace("_animated", "-animated")

      for component in components:
        component_path = THEME_SAVE_PATH / "theme_packs" / theme_folder_name / component
        if not component_path.is_dir() or not any(component_path.iterdir()):
          print(f"Missing or empty component '{component}' for theme '{theme_folder_name}'. Downloading...")
          self.download_theme(component, theme_folder_name, THEME_COMPONENT_PARAMS.get(component), starpilot_toggles)
          self.update_active_theme(True, starpilot_toggles)

    wheels_path = THEME_SAVE_PATH / "steering_wheels"
    for display_name in downloaded_data.get("steering_wheels", []):
      file_stem = display_name.replace(" ", "_").lower()
      matching_files = list(wheels_path.glob(f"{file_stem}.*"))
      if not matching_files:
        print(f"Missing steering wheel '{display_name}'. Downloading...")
        self.download_theme("steering_wheels", file_stem, THEME_COMPONENT_PARAMS["steering_wheels"], starpilot_toggles)
        self.update_active_theme(True, starpilot_toggles)

    protected_dirs = {THEME_SAVE_PATH / "bootlogos", THEME_SAVE_PATH / "theme_packs", THEME_SAVE_PATH / "steering_wheels"}
    for dir_path in THEME_SAVE_PATH.glob("**/*"):
      if dir_path.is_dir() and not any(dir_path.iterdir()):
        if dir_path in protected_dirs:
          continue
        print(f"Deleting empty folder: {dir_path}")
        delete_file(dir_path)
      elif dir_path.is_file() and dir_path.name.startswith("tmp"):
        print(f"Deleting temp file: {dir_path}")
        delete_file(dir_path)

    print("Theme validation complete.")
