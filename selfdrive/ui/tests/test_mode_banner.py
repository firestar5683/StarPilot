from openpilot.selfdrive.ui.lib.mode_banner import ModeBannerVariant, get_mode_banner_variant, mode_atom_color, mode_banner_color


class FakeParams:
  def __init__(self, bools=None, ints=None):
    self.bools = bools or {}
    self.ints = ints or {}

  def get_bool(self, key):
    return self.bools.get(key, False)

  def get_int(self, key, default=0):
    return self.ints.get(key, default)


def _rgb(color):
  return color.r, color.g, color.b


def test_mode_banner_variant_tracks_longitudinal_preference():
  assert get_mode_banner_variant(FakeParams()) == ModeBannerVariant.CHILL
  assert get_mode_banner_variant(FakeParams(ints={"LongitudinalModelPreference": 1})) == ModeBannerVariant.EXPERIMENTAL
  assert get_mode_banner_variant(FakeParams({"SafeMode": True}, {"LongitudinalModelPreference": 1})) == ModeBannerVariant.CHILL


def test_atom_gradients_use_compact_icon_directions():
  assert _rgb(mode_atom_color(ModeBannerVariant.CHILL, 0.0)) == (35, 149, 255)
  assert _rgb(mode_atom_color(ModeBannerVariant.CHILL, 1.0)) == (20, 255, 171)
  assert _rgb(mode_atom_color(ModeBannerVariant.EXPERIMENTAL, 0.0)) == (255, 155, 63)
  assert _rgb(mode_atom_color(ModeBannerVariant.EXPERIMENTAL, 1.0)) == (219, 56, 34)
