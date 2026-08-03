STARPILOT_DISPLAY_VERSION = "6.7.4"


def starpilot_display_description(description: str | None) -> str:
  if not description:
    return ""

  parts = [part.strip() for part in description.split(" / ")]
  if not parts:
    return STARPILOT_DISPLAY_VERSION

  parts[0] = STARPILOT_DISPLAY_VERSION
  return " / ".join(parts)
