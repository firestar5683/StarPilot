"""Opt-in desktop presentation of the unchanged native canvas, with letterboxing."""
import os
import sys


def viewport(width, height, canvas_width, canvas_height):
  scale=min(width/canvas_width,height/canvas_height)
  return ((width-canvas_width*scale)/2,(height-canvas_height*scale)/2,
          canvas_width*scale,canvas_height*scale)


class FullscreenCanvas:
  def __init__(self, rl, app):
    self.rl,self.app=rl,app
    self.base_scale=app._scale
    self.rect=(0.,0.,float(app._scaled_width),float(app._scaled_height))
    self.size=None

  def toggle(self):
    self.rl.toggle_borderless_windowed()

  def update(self):
    rl,app=self.rl,self.app
    if rl.is_key_pressed(rl.KeyboardKey.KEY_F11) or rl.is_key_pressed(rl.KeyboardKey.KEY_F):self.toggle()
    elif rl.is_key_pressed(rl.KeyboardKey.KEY_ESCAPE) and rl.is_window_state(rl.ConfigFlags.FLAG_BORDERLESS_WINDOWED_MODE):self.toggle()
    width,height=max(1,rl.get_screen_width()),max(1,rl.get_screen_height())
    size=(width,height,max(1,rl.get_render_width()),max(1,rl.get_render_height()))
    if size==self.size:return
    self.size=size
    self.rect=viewport(width,height,app.width,app.height)
    pixel_width=max(1,round(self.rect[2]*size[2]/width))
    pixel_height=max(1,round(self.rect[3]*size[3]/height))
    if app._render_texture is not None:rl.unload_render_texture(app._render_texture)
    app._render_texture=rl.load_render_texture(pixel_width,pixel_height)
    rl.set_texture_filter(app._render_texture.texture,rl.TextureFilter.TEXTURE_FILTER_BILINEAR)
    app._render_texture_width,app._render_texture_height=pixel_width,pixel_height
    app._pixel_scale_x=pixel_width/(app.width*app._scale)
    app._pixel_scale_y=pixel_height/(app.height*app._scale)
    app._patch_scissor_mode()

  def map_event(self, event):
    x,y,width,height=self.rect
    position=event.pos
    mapped=type(position)((position.x*self.base_scale-x)*self.app.width/width,
                          (position.y*self.base_scale-y)*self.app.height/height)
    return event._replace(pos=mapped)


def install(rl, app, *, environ=None, platform=None):
  env=os.environ if environ is None else environ
  if ((sys.platform if platform is None else platform)!='darwin'
      or env.get('ROADSCORE_FULLSCREEN')!='1' or env.get('ROADSCORE_PREPARED_SHOWCASE')!='1'
      or env.get('SIMULATION')!='1' or env.get('BIG','0')!='0'):
    return False
  original_init=app.init_window
  original_progress=app._mark_progress
  original_draw=rl.draw_texture_pro
  original_events=app._mouse.get_events
  canvas=FullscreenCanvas(rl,app)
  def init_window(*args,**kwargs):
    result=original_init(*args,**kwargs)
    rl.set_exit_key(rl.KeyboardKey.KEY_NULL)
    canvas.toggle()
    canvas.update()
    return result
  def progress(label):
    # Before mouse collection and render-target binding, never during drawing.
    if label=='gui_app.loop_start':canvas.update()
    return original_progress(label)
  def draw(texture,source,destination,origin,rotation,tint):
    if app._render_texture is not None and texture.id==app._render_texture.texture.id:
      destination=rl.Rectangle(*canvas.rect)
    return original_draw(texture,source,destination,origin,rotation,tint)
  def events():return [canvas.map_event(event) for event in original_events()]
  app.init_window=init_window
  app._mark_progress=progress
  app._mouse.get_events=events
  rl.draw_texture_pro=draw
  app._roadscore_fullscreen=canvas
  return True
