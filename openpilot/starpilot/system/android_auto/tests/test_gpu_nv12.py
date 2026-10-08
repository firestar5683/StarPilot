"""Pixel-level GPU regression checks; run with STARPILOT_AUTO_GL_TEST=1 on a desktop or comma.

The expected image is the car view's RGBA composition read back, followed by the
CPU NV12 reference. This catches flipped rows, margin placement and chroma blocks
that straddle the padding without duplicating the shader's coordinate logic.
"""

import ctypes as C
import os
import sys
from unittest import SkipTest

import numpy as np
import pytest
from unittest.mock import Mock

from openpilot.starpilot.system.android_auto import gpu_nv12, headless_egl


@pytest.mark.parametrize("margins", [(-1, 0), (32, 0), (0, -1), (0, 18)])
def test_invalid_margins_leave_no_gpu_resources(margins):
  with pytest.raises(ValueError, match="margins"):
    gpu_nv12.Nv12Converter(32, 18, margin_w=margins[0], margin_h=margins[1])


@pytest.fixture(scope="module")
def gpu():
  if os.getenv("STARPILOT_AUTO_GL_TEST") != "1":
    raise SkipTest("STARPILOT_AUTO_GL_TEST=1 enables tests requiring a real graphics context")
  import pyray as rl
  with pytest.MonkeyPatch.context() as patch:
    if sys.platform == "darwin":
      gl = C.CDLL("/System/Library/Frameworks/OpenGL.framework/OpenGL")
      # A windowless CGL context also works in a terminal without a Cocoa app.
      gl.CGLChoosePixelFormat.argtypes = [C.POINTER(C.c_int), C.POINTER(C.c_void_p), C.POINTER(C.c_int)]
      gl.CGLCreateContext.argtypes = [C.c_void_p, C.c_void_p, C.POINTER(C.c_void_p)]
      gl.CGLSetCurrentContext.argtypes = [C.c_void_p]
      gl.CGLDestroyContext.argtypes = [C.c_void_p]
      gl.CGLDestroyPixelFormat.argtypes = [C.c_void_p]
      pixel_format, context, count = C.c_void_p(), C.c_void_p(), C.c_int()
      # kCGLPFAOpenGLProfile, kCGLOGLPVersion_3_2_Core, kCGLPFAColorSize
      assert gl.CGLChoosePixelFormat((C.c_int * 5)(99, 0x3200, 8, 24, 0), C.byref(pixel_format), C.byref(count)) == 0
      assert gl.CGLCreateContext(pixel_format, None, C.byref(context)) == 0
      gl.CGLDestroyPixelFormat(pixel_format)
      assert gl.CGLSetCurrentContext(context) == 0
      patch.setattr(headless_egl.C, "CDLL", lambda _: gl)
      loader_type = C.CFUNCTYPE(C.c_void_p, C.c_char_p)
      def address(name):
        function = getattr(gl, name.decode(), None)
        return C.cast(function, C.c_void_p).value if function is not None else None
      loader = loader_type(address)
      rl.rl_load_extensions(rl.ffi.cast("void *", C.cast(loader, C.c_void_p).value))
      rl.rlgl_init(64, 64)
      rl.rl_set_framebuffer_width(64)
      rl.rl_set_framebuffer_height(64)

      def close():
        rl.rlgl_close()
        gl.CGLSetCurrentContext(None)
        gl.CGLDestroyContext(context)
    else:
      context = headless_egl.HeadlessContext(64, 64)
      close = context.close
    try:
      yield rl
    finally:
      close()


def read_frame(size, regions, asynchronous=False):
  readback = headless_egl.FrameReadback(size, asynchronous=asynchronous)
  try:
    readback.start(regions)
    return bytes(readback.finish())
  finally:
    readback.close()



@pytest.mark.parametrize("width,height,margin_w,margin_h", [(32, 18, 0, 0), (32, 18, 4, 2), (32, 20, 3, 5), (40, 18, 0, 6)])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_composed_car_frame_converts_to_the_same_picture(gpu, width, height, margin_w, margin_h, asynchronous):
  """The RGBA fallback's explicit composition retains exact NV12 colors."""
  rl = gpu
  logical_w, logical_h = 31, 18  # the projection's logical canvas, scaled to fit the visible area
  pixels = np.random.default_rng(11).integers(0, 256, (logical_h, logical_w, 4), dtype=np.uint8)
  buffer = rl.ffi.from_buffer(pixels)
  texture_id = rl.rl_load_texture(rl.ffi.cast("void *", buffer), logical_w, logical_h, 7, 1)
  source = rl.Texture(texture_id, logical_w, logical_h, 1, 7)
  output = rl.load_render_texture(width, height)
  converter = gpu_nv12.Nv12Converter(width, height)
  try:
    gpu_nv12.compose_rgba(source, output, margin_w, margin_h, fit=True)
    rgba = read_frame(width * height * 4, [(output.id, width, height, 0)])
    nv12 = read_frame(width * height * 3 // 2, converter.convert(output.texture), asynchronous)
    assert nv12 == gpu_nv12.reference_nv12(rgba, width, height)
  finally:
    converter.close()
    rl.unload_render_texture(output)
    rl.rl_unload_texture(texture_id)


@pytest.mark.parametrize("width,height,margin_w,margin_h", [(32, 18, 0, 0), (32, 18, 4, 2), (32, 20, 3, 5)])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_fused_projection_conversion_matches_rgba_composition(gpu, width, height, margin_w, margin_h, asynchronous):
  """The fast car path folds margins and vertical orientation into NV12 conversion."""
  rl = gpu
  visible_w, visible_h = width - margin_w, height - margin_h
  pixels = np.random.default_rng(17).integers(0, 256, (visible_h, visible_w, 4), dtype=np.uint8)
  buffer = rl.ffi.from_buffer(pixels)
  texture_id = rl.rl_load_texture(rl.ffi.cast("void *", buffer), visible_w, visible_h, 7, 1)
  source = rl.Texture(texture_id, visible_w, visible_h, 1, 7)
  output = rl.load_render_texture(width, height)
  converter = gpu_nv12.Nv12Converter(width, height, margin_w=margin_w, margin_h=margin_h, compose=True)
  try:
    gpu_nv12.compose_rgba(source, output, margin_w, margin_h)
    rgba = read_frame(width * height * 4, [(output.id, width, height, 0)])
    nv12 = read_frame(width * height * 3 // 2, converter.convert(source), asynchronous)
    assert nv12 == gpu_nv12.reference_nv12(rgba, width, height)
  finally:
    converter.close()
    rl.unload_render_texture(output)
    rl.rl_unload_texture(texture_id)


def test_failed_async_readback_reports_gl_error_and_falls_back_to_sync(monkeypatch):
  gl = Mock()
  gl.glFenceSync.return_value = 1
  gl.glClientWaitSync.return_value = headless_egl.GL_WAIT_FAILED
  gl.glGetError.return_value = 0x502
  monkeypatch.setattr(headless_egl.C, "CDLL", lambda _name: gl)
  readback = headless_egl.FrameReadback(16, asynchronous=True)
  readback.start([(7, 2, 2, 0)])
  with pytest.raises(RuntimeError, match="0x911d, GL error 0x502"):
    readback.finish()
  readback.release()
  readback.fall_back_to_sync()
  readback.start([(7, 2, 2, 0)])
  assert not readback.asynchronous and readback.finish() is readback.pixels
  readback.close()
