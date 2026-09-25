"""Real interface/GPS owners for tests that call Card publication in isolation."""
from typing import Any

from opendbc.car.car_helpers import interfaces
from opendbc.car.mock.interface import CarInterface as MockInterface
from openpilot.starpilot.gps.publisher import CarGpsPublisher


def initialize_publication_sources(card: Any) -> None:
  cp = card.CP
  interface = interfaces[cp.carFingerprint] if cp.brand else MockInterface
  card.CI = interface(cp)
  card.car_gps_publisher = CarGpsPublisher()
