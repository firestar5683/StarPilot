import unittest
import tempfile
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole, Profile, font_filename, font_path, validate_bitmap_font


class TestBitmapFonts(unittest.TestCase):
  def test_supplied_sora_brand_is_pinned_and_independent_of_external_font_bundle(self):
    filename = font_filename(Profile.COMPACT, FontRole.BRAND)
    self.assertEqual(filename, "Sora-800.fnt")
    path = font_path(Path("/unavailable-external-fonts"), filename)
    self.assertEqual(path.parent.name, "fonts")
    validate_bitmap_font(path)
    metadata = json.loads(path.parents[2].joinpath("sora-brand-font.json").read_text())
    self.assertEqual((metadata["source"]["axis"], metadata["source"]["value"]), ("wght", 800))

  def test_invalid_descriptor_is_rejected_before_native_parser(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "font.fnt"
      path.write_text("not a bitmap font\n")
      with self.assertRaisesRegex(ValueError, "Invalid bitmap font"):
        validate_bitmap_font(path)

  def test_changed_atlas_is_rejected_even_with_reviewed_descriptor(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "Inter-Regular.fnt"
      descriptor, atlas = b'reviewed descriptor', b'reviewed atlas'
      path.write_bytes(descriptor)
      path.with_suffix('.png').write_bytes(atlas)
      manifest = {'files': [{'file': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                            for name, data in ((path.name, descriptor), (path.with_suffix('.png').name, atlas))]}
      with patch.object(Path, 'read_text', return_value=json.dumps(manifest)):
        validate_bitmap_font(path)
        path.with_suffix('.png').write_bytes(b'corrupt atlas')
        with self.assertRaisesRegex(ValueError, 'reviewed font manifest'):
          validate_bitmap_font(path)

  def test_requires_context_before_native_allocation(self):
    with patch("openpilot.starpilot.ui.presentation.rl.is_window_ready", return_value=False), \
         patch("openpilot.starpilot.ui.presentation.rl.load_font") as load:
      with self.assertRaisesRegex(RuntimeError, "graphics context"):
        BitmapFonts(Profile.LARGE, Path("unused"))
      load.assert_not_called()

  def test_failed_resource_load_releases_previously_loaded_fonts(self):
    allocated = SimpleNamespace(texture=SimpleNamespace(id=1), glyphCount=1)
    with patch("openpilot.starpilot.ui.presentation.rl.is_window_ready", return_value=True), \
         patch("openpilot.starpilot.ui.presentation.validate_bitmap_font"), \
         patch("openpilot.starpilot.ui.presentation.rl.get_font_default", return_value=SimpleNamespace(texture=SimpleNamespace(id=99))), \
         patch.object(Path, "is_file", return_value=True), \
         patch("openpilot.starpilot.ui.presentation.rl.load_font", side_effect=[allocated, RuntimeError("broken asset")]), \
         patch("openpilot.starpilot.ui.presentation.rl.gen_texture_mipmaps"), \
         patch("openpilot.starpilot.ui.presentation.rl.set_texture_filter"), \
         patch("openpilot.starpilot.ui.presentation.rl.unload_font") as unload:
      with self.assertRaisesRegex(RuntimeError, "broken asset"):
        BitmapFonts(Profile.LARGE, Path("unused"))
      unload.assert_called_once_with(allocated)

  def test_failed_load_cannot_adopt_or_unload_the_shared_default_font(self):
    default = SimpleNamespace(texture=SimpleNamespace(id=99), glyphCount=95)
    with patch("openpilot.starpilot.ui.presentation.rl.is_window_ready", return_value=True), \
         patch("openpilot.starpilot.ui.presentation.validate_bitmap_font"), \
         patch("openpilot.starpilot.ui.presentation.rl.get_font_default", return_value=default), \
         patch.object(Path, "is_file", return_value=True), \
         patch("openpilot.starpilot.ui.presentation.rl.load_font", return_value=default), \
         patch("openpilot.starpilot.ui.presentation.rl.unload_font") as unload:
      with self.assertRaisesRegex(RuntimeError, "Unable to load bitmap font"):
        BitmapFonts(Profile.LARGE, Path("unused"))
      unload.assert_not_called()

  def test_drawing_does_not_double_apply_an_application_text_scale(self):
    fonts = object.__new__(BitmapFonts)
    fonts.profile = Profile.COMPACT
    fonts._fonts = {"Inter-Regular.fnt": SimpleNamespace(texture=SimpleNamespace(id=1))}
    with patch("openpilot.starpilot.ui.presentation.rl._orig_draw_text_ex", create=True) as raw_draw, \
         patch("openpilot.starpilot.ui.presentation.rl.draw_text_ex") as scaled_draw:
      fonts.draw("sample", FontRole.ROMAN, 36, 10, 20)
      scaled_draw.assert_not_called()
      self.assertAlmostEqual(raw_draw.call_args.args[3], 36 * 1.16)


if __name__ == "__main__":
  unittest.main()
