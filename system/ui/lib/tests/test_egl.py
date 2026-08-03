import cffi

from openpilot.system.ui.lib import egl


def test_external_texture_has_its_own_gl_target(monkeypatch):
  calls = []
  ffi = cffi.FFI()

  def gen_textures(count, textures):
    calls.append(("generate", count))
    textures[0] = 23

  state = egl.EGLState(
    initialized=True,
    ffi=ffi,
    get_gl_error=lambda: egl.GL_NO_ERROR,
    active_texture=lambda texture: calls.append(("active", texture)),
    bind_texture=lambda target, texture: calls.append(("bind", target, texture)),
    gen_textures=gen_textures,
    delete_textures=lambda count, textures: calls.append(("delete", count, int(textures[0]))),
  )
  monkeypatch.setattr(egl, "_egl", state)

  texture_id = egl.create_external_texture()
  egl.destroy_external_texture(texture_id)

  assert texture_id == 23
  assert calls == [
    ("generate", 1),
    ("active", egl.GL_TEXTURE0),
    ("bind", egl.GL_TEXTURE_EXTERNAL_OES, 23),
    ("delete", 1, 23),
  ]
