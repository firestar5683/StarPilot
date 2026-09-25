from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole, Profile, font_filename


def test_compact_set_speed_uses_custom_face_without_changing_current_speed():
  assert font_filename(Profile.COMPACT, FontRole.SET_SPEED) == "DINish-Speed.fnt"
  assert font_filename(Profile.COMPACT, FontRole.SPEED) == "Inter-Bold.fnt"
  assert font_filename(Profile.COMPACT, FontRole.DISPLAY) == "Inter-Bold.fnt"
  assert font_filename(Profile.COMPACT, FontRole.SEMI_BOLD) == "Inter-SemiBold.fnt"


def test_speed_optical_style_is_scoped_to_requested_faces():
  fonts = BitmapFonts.__new__(BitmapFonts)
  fonts.profile = Profile.LARGE
  assert fonts._optical_style(FontRole.SPEED) == (1.04, .85)
  assert fonts._optical_style(FontRole.BRAND) == (1., 0.)
  fonts.profile = Profile.COMPACT
  assert fonts._optical_style(FontRole.SET_SPEED) == (1., .65)
  assert fonts._optical_style(FontRole.SPEED) == (1., 0.)
  assert fonts._optical_style(FontRole.DISPLAY) == (1., 0.)
  assert fonts._optical_style(FontRole.SET_SPEED, fallback=True) == (1., 0.)
