# ruff: noqa: INP001
from pathlib import Path


GENERIC_LFAHDA = "BO_ 1157 LFAHDA_MFC: 4 XXX"
REFRESH_LFAHDA = "BO_ 1157 LFAHDA_MFC: 8 XXX"


def generate() -> dict[str, str]:
  source = Path(__file__).with_name("hyundai_can.dbc").read_text(encoding="utf-8")
  if source.count(GENERIC_LFAHDA) != 1:
    raise RuntimeError("expected exactly one 4-byte LFAHDA_MFC definition")
  return {"hyundai_can_refresh.dbc": source.replace(GENERIC_LFAHDA, REFRESH_LFAHDA, 1)}
