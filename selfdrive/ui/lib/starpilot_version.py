STARPILOT_DISPLAY_VERSION = "6.7.6"
DEFAULT_HOME_SCREEN_NAME = "StarPilot"
HOME_SCREEN_NAME_MAX_LENGTH = 12


def normalize_home_screen_name(value: str | bytes | None) -> str:
  if isinstance(value, bytes):
    value = value.decode("utf-8", errors="ignore")

  name = str(value or "").strip()[:HOME_SCREEN_NAME_MAX_LENGTH]
  return name or DEFAULT_HOME_SCREEN_NAME


def home_screen_name(params) -> str:
  try:
    value = params.get("HomeScreenName", encoding="utf-8")
  except TypeError:
    value = params.get("HomeScreenName")

  if not value:
    try:
      value = params.get_default_value("HomeScreenName")
    except (AttributeError, KeyError):
      value = DEFAULT_HOME_SCREEN_NAME

  return normalize_home_screen_name(value)


def starpilot_display_description(description: str | None) -> str:
  if not description:
    return ""

  parts = [part.strip() for part in description.split(" / ")]
  if not parts:
    return STARPILOT_DISPLAY_VERSION

  parts[0] = STARPILOT_DISPLAY_VERSION
  return " / ".join(parts)
