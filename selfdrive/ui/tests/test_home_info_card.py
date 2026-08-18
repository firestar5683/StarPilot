import json

import pyray as rl

from openpilot.selfdrive.ui.widgets.home_info_card import HomeInfoCard
from openpilot.starpilot.navigation.destination_store import (
  FAVORITE_DESTINATIONS_KEY,
  NAVIGATION_DESTINATION_KEY,
  RECENT_DESTINATIONS_KEY,
  same_destination,
)


class FakeParams:
  def __init__(self, values=None):
    self.values = dict(values or {})
    self.writes = []

  def get(self, key, encoding=None, default=None):
    value = self.values.get(key, default)
    if encoding == "utf-8" and isinstance(value, bytes):
      return value.decode("utf-8")
    return value

  def put(self, key, value):
    self.values[key] = value
    self.writes.append((key, value))


class FakeDriveStats:
  def __init__(self):
    self.records_rendered = 0

  def render_records(self, _rect):
    self.records_rendered += 1


def _favorite(name, latitude, longitude, **flags):
  return {"name": name, "latitude": latitude, "longitude": longitude, **flags}


def _card(params, *, online_provider=lambda: True, gps_provider=lambda: True):
  card = HomeInfoCard(params, FakeDriveStats(), online_provider=online_provider, gps_provider=gps_provider)
  card.set_rect(rl.Rectangle(100, 200, 750, 745))
  card.refresh()
  return card


def test_quick_start_requires_secret_and_at_least_one_valid_favorite():
  no_secret = _card(FakeParams({
    FAVORITE_DESTINATIONS_KEY: json.dumps([_favorite("Home", 1, 2)]),
  }))
  no_valid_favorites = _card(FakeParams({
    "MapboxSecretKey": "secret",
    FAVORITE_DESTINATIONS_KEY: json.dumps([_favorite("Overflow", 10 ** 1000, 2)]),
  }))
  one_favorite = _card(FakeParams({
    "MapboxSecretKey": "secret",
    FAVORITE_DESTINATIONS_KEY: json.dumps([_favorite("Home", 1, 2)]),
  }))

  assert not no_secret.quick_start_available
  assert no_secret.show_records
  assert not no_valid_favorites.quick_start_available
  assert no_valid_favorites.show_records
  assert one_favorite.quick_start_available
  assert not one_favorite.show_records


def test_quick_start_uses_canonical_order_and_three_row_limit():
  params = FakeParams({
    "MapboxSecretKey": "secret",
    FAVORITE_DESTINATIONS_KEY: json.dumps([
      _favorite("Zulu", 1, 1),
      _favorite("Work", 2, 2, is_work=True),
      _favorite("Bravo", 3, 3),
      _favorite("Home", 4, 4, is_home=True),
      _favorite("Alpha", 5, 5),
    ]),
  })

  card = _card(params)

  assert [favorite["name"] for favorite in card.favorites] == ["Home", "Work", "Alpha"]


def test_page_switch_is_in_memory_and_destination_rows_select_once():
  params = FakeParams({
    "MapboxSecretKey": "secret",
    FAVORITE_DESTINATIONS_KEY: json.dumps([_favorite("Home", 1, 2)]),
    RECENT_DESTINATIONS_KEY: [],
  })
  card = _card(params)

  flip_center = rl.Vector2(card._flip_rect.x + card._flip_rect.width / 2, card._flip_rect.y + card._flip_rect.height / 2)
  card._handle_mouse_release(flip_center)
  assert card.show_records
  card._handle_mouse_release(flip_center)
  assert not card.show_records

  row = card._destination_rects[0]
  row_center = rl.Vector2(row.x + row.width / 2, row.y + row.height / 2)
  card._handle_mouse_release(row_center)
  assert json.loads(params.values[NAVIGATION_DESTINATION_KEY])["name"] == "Home"
  assert params.values[RECENT_DESTINATIONS_KEY][0]["place_name"] == "Home"
  first_write_count = len(params.writes)
  assert card.active_destination["name"] == "Home"

  card._handle_mouse_release(row_center)
  assert len(params.writes) == first_write_count


def test_refresh_falls_back_without_clearing_an_active_non_favorite_destination():
  active = {"name": "Old destination", "latitude": 9, "longitude": 10}
  params = FakeParams({
    "MapboxSecretKey": "secret",
    FAVORITE_DESTINATIONS_KEY: json.dumps([_favorite("Home", 1, 2)]),
    NAVIGATION_DESTINATION_KEY: json.dumps(active),
  })
  card = _card(params)

  assert card.active_destination["name"] == "Old destination"
  assert all(not same_destination(card.active_destination, favorite) for favorite in card.favorites)

  params.values["MapboxSecretKey"] = ""
  card.refresh()
  assert not card.quick_start_available
  assert card.show_records
  assert card.active_destination["name"] == "Old destination"


def test_quick_start_requires_online_and_gps():
  params = FakeParams({
    "MapboxSecretKey": "secret",
    FAVORITE_DESTINATIONS_KEY: json.dumps([_favorite("Home", 1, 2)]),
  })

  # Both online and GPS available
  card = _card(params, online_provider=lambda: True, gps_provider=lambda: True)
  assert card.quick_start_available
  assert not card.show_records

  # Offline
  card_offline = _card(params, online_provider=lambda: False, gps_provider=lambda: True)
  assert not card_offline.quick_start_available
  assert card_offline.show_records

  # No GPS fix
  card_no_gps = _card(params, online_provider=lambda: True, gps_provider=lambda: False)
  assert not card_no_gps.quick_start_available
  assert card_no_gps.show_records

  # Fallback GPS check via LastGPSPosition in params
  params_with_gps = FakeParams({
    "MapboxSecretKey": "secret",
    FAVORITE_DESTINATIONS_KEY: json.dumps([_favorite("Home", 1, 2)]),
    "LastGPSPosition": json.dumps({"latitude": 37.77, "longitude": -122.41, "hasFix": True}),
  })
  card_param_gps = HomeInfoCard(params_with_gps, FakeDriveStats(), online_provider=lambda: True)
  card_param_gps.set_rect(rl.Rectangle(100, 200, 750, 745))
  card_param_gps.refresh()
  assert card_param_gps.quick_start_available

  # LastGPSPosition with hasFix=False or Null Island -> unavailable
  params_bad_gps = FakeParams({
    "MapboxSecretKey": "secret",
    FAVORITE_DESTINATIONS_KEY: json.dumps([_favorite("Home", 1, 2)]),
    "LastGPSPosition": json.dumps({"latitude": 0.0, "longitude": 0.0, "hasFix": False}),
  })
  card_bad_gps = HomeInfoCard(params_bad_gps, FakeDriveStats(), online_provider=lambda: True)
  card_bad_gps.set_rect(rl.Rectangle(100, 200, 750, 745))
  card_bad_gps.refresh()
  assert not card_bad_gps.quick_start_available

