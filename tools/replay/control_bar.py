#!/usr/bin/env python3
"""
Standalone replay media controls bar for StarPilot desktop replay.
Compact always-on-top window with probe-rod scrubber and transport buttons.
"""
import os
import json
import pyray as rl

# ── Config ──────────────────────────────────────
W, H = 460, 64

# Colours
BG        = rl.Color(18, 18, 22, 245)
TRACK_COL = rl.Color(55, 55, 65, 255)
FILL_COL  = rl.Color(0, 200, 130, 255)
KNOB_COL  = rl.WHITE
BTN_HOV   = rl.Color(255, 255, 255, 28)
TXT_DIM   = rl.Color(175, 175, 185, 255)
TXT_HOT   = rl.WHITE
SEP_COL   = rl.Color(60, 60, 72, 255)
PIN_ON    = rl.Color(0, 200, 130, 255)
PIN_OFF   = rl.Color(90, 90, 100, 255)


def pid_alive(pid: int) -> bool:
  try:
    os.kill(pid, 0)
    return True
  except OSError:
    return False


def format_time(seconds: float) -> str:
  s = int(seconds)
  return f"{s // 60:02d}:{s % 60:02d}"


def draw_btn(font, text: str, rect: rl.Rectangle, mouse: rl.Vector2, fsize: int = 12) -> bool:
  hovered = rl.check_collision_point_rec(mouse, rect)
  if hovered:
    rl.draw_rectangle_rounded(rect, 0.35, 6, BTN_HOV)
  tw = rl.measure_text_ex(font, text, fsize, 0)
  tx = rect.x + (rect.width  - tw.x) / 2
  ty = rect.y + (rect.height - tw.y) / 2
  rl.draw_text_ex(font, text, rl.Vector2(tx, ty), fsize, 0,
                  TXT_HOT if hovered else TXT_DIM)
  return hovered and rl.is_mouse_button_pressed(rl.MouseButton.MOUSE_BUTTON_LEFT)


def main():
  prefix    = os.getenv("OPENPILOT_PREFIX", "default")
  state_f   = f"/tmp/replay_state_{prefix}.json"
  cmd_f     = f"/tmp/replay_cmd_{prefix}.json"

  # PIDs to watch — exit when ALL are dead
  watch_pids: list[int] = []
  raw = os.getenv("REPLAY_WATCH_PIDS", "")
  if raw.strip():
    for tok in raw.split():
      try:
        watch_pids.append(int(tok))
      except ValueError:
        pass

  # ── Init window ────────────────────────────────
  rl.init_window(W, H, "Replay Controls")
  rl.set_target_fps(60)

  # Position: bottom-right corner, clear of taskbar
  mon_w = rl.get_monitor_width(0) or 1920
  mon_h = rl.get_monitor_height(0) or 1080
  rl.set_window_position(mon_w - W - 20, mon_h - H - 60)

  # Always on top by default
  rl.set_window_state(rl.ConfigFlags.FLAG_WINDOW_TOPMOST)

  # Load font (Inter-Medium.fnt — same as rest of desktop UI)
  basedir = os.environ.get("BASEDIR", "") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
  font_path = os.path.join(basedir, "selfdrive", "assets", "fonts", "Inter-Medium.fnt")
  if os.path.exists(font_path):
    font = rl.load_font(font_path)
    rl.gen_texture_mipmaps(font.texture)
    rl.set_texture_filter(font.texture, rl.TextureFilter.TEXTURE_FILTER_TRILINEAR)
  else:
    font = rl.get_font_default()

  # State
  min_sec = max_sec = cur_sec = 0.0
  paused  = False
  speed   = 1.0
  dragging = False
  pinned   = True

  # Cleanup leftover cmd file
  try:
    os.remove(cmd_f)
  except Exception:
    pass

  SPEEDS = [0.5, 1.0, 1.5, 2.0, 3.0]

  # ── Main loop ──────────────────────────────────
  while not rl.window_should_close():

    # Exit if all watched parent processes have died
    if watch_pids and not any(pid_alive(p) for p in watch_pids):
      break

    # Read state
    try:
      with open(state_f) as f:
        s = json.load(f)
      min_sec = s.get("min_sec", 0.0)
      max_sec = s.get("max_sec", 0.0)
      if not dragging:
        cur_sec = s.get("cur_sec", 0.0)
      paused  = s.get("paused", False)
      speed   = s.get("speed", 1.0)
    except Exception:
      pass

    mouse = rl.get_mouse_position()

    # ── Layout constants ───────────────────────
    PAD  = 8
    SL_Y = 15    # scrubber centre y
    SL_H = 4     # track height
    BW   = 46    # button width
    BH   = 22    # button height
    BY   = H - BH - 8  # button row y

    TL_W = 36
    SL_X = PAD + TL_W + 4
    SL_W = W - SL_X - TL_W - PAD - 4

    # ── Scrubber drag ──────────────────────────
    has_data = max_sec > min_sec
    if has_data:
      drag_rect = rl.Rectangle(SL_X - 4, 0, SL_W + 8, SL_Y + 12)
      if rl.is_mouse_button_pressed(rl.MouseButton.MOUSE_BUTTON_LEFT):
        if rl.check_collision_point_rec(mouse, drag_rect):
          dragging = True
      if dragging:
        if rl.is_mouse_button_down(rl.MouseButton.MOUSE_BUTTON_LEFT):
          p = max(0.0, min(1.0, (mouse.x - SL_X) / SL_W))
          cur_sec = min_sec + p * (max_sec - min_sec)
          try:
            with open(cmd_f, "w") as f:
              json.dump({"seek": cur_sec}, f)
          except Exception:
            pass
        else:
          dragging = False

    # ── Draw ───────────────────────────────────
    rl.begin_drawing()
    rl.clear_background(BG)

    # Top separator line
    rl.draw_rectangle(0, 0, W, 1, SEP_COL)

    if has_data:
      prog = max(0.0, min(1.0, (cur_sec - min_sec) / (max_sec - min_sec)))

      # Track background
      rl.draw_rectangle(SL_X, SL_Y - SL_H // 2, SL_W, SL_H, TRACK_COL)
      # Fill
      fill_w = int(SL_W * prog)
      if fill_w > 0:
        rl.draw_rectangle(SL_X, SL_Y - SL_H // 2, fill_w, SL_H, FILL_COL)
      # Knob
      kx = int(SL_X + SL_W * prog)
      rl.draw_circle(kx, SL_Y, 6 if dragging else 4, KNOB_COL)

      # Time labels
      rl.draw_text_ex(font, format_time(cur_sec),
                      rl.Vector2(PAD, SL_Y - 6), 12, 0, TXT_DIM)
      rl.draw_text_ex(font, format_time(max_sec),
                      rl.Vector2(W - PAD - TL_W + 2, SL_Y - 6), 12, 0, TXT_DIM)

      # ── Button row ────────────────────────────
      # Layout (left → right): |<  -10s  PLAY/PAUSE  +10s  >|  speed  pin
      total_btns  = 7
      gap         = 4
      seg_bw      = 28     # |< and >|
      speed_bw    = 36
      pin_bw      = 26
      inner_w     = W - 2 * PAD
      play_bw     = inner_w - 2 * seg_bw - 2 * BW - speed_bw - pin_bw - gap * (total_btns - 1)
      play_bw     = max(48, play_bw)

      cx = PAD

      def btn(label, bw):
        nonlocal cx
        r = rl.Rectangle(cx, BY, bw, BH)
        cx += bw + gap
        return draw_btn(font, label, r, mouse, 12)

      if btn("|<", seg_bw):
        seg = int(cur_sec / 60)
        target = ((seg - 1) if cur_sec - seg * 60 < 2 and seg > 0 else seg) * 60.0
        try:
          with open(cmd_f, "w") as f:
            json.dump({"seek": max(min_sec, target)}, f)
        except Exception:
          pass

      if btn("-10", BW):
        try:
          with open(cmd_f, "w") as f:
            json.dump({"seek": max(min_sec, cur_sec - 10.0)}, f)
        except Exception:
          pass

      if btn("PAUSE" if not paused else "PLAY", play_bw):
        try:
          with open(cmd_f, "w") as f:
            json.dump({"play": paused}, f)
        except Exception:
          pass

      if btn("+10", BW):
        try:
          with open(cmd_f, "w") as f:
            json.dump({"seek": min(max_sec, cur_sec + 10.0)}, f)
        except Exception:
          pass

      if btn(">|", seg_bw):
        seg = int(cur_sec / 60)
        try:
          with open(cmd_f, "w") as f:
            json.dump({"seek": min(max_sec, (seg + 1) * 60.0)}, f)
        except Exception:
          pass

      if btn(f"{speed:.1f}x", speed_bw):
        try:
          idx = SPEEDS.index(speed)
        except ValueError:
          idx = 0
        next_speed = SPEEDS[(idx + 1) % len(SPEEDS)]
        try:
          with open(cmd_f, "w") as f:
            json.dump({"speed": next_speed}, f)
        except Exception:
          pass

      # Pin (always-on-top) toggle
      pin_rect = rl.Rectangle(cx, BY, pin_bw, BH)
      hovered = rl.check_collision_point_rec(mouse, pin_rect)
      if hovered:
        rl.draw_rectangle_rounded(pin_rect, 0.35, 6, BTN_HOV)
        if rl.is_mouse_button_pressed(rl.MouseButton.MOUSE_BUTTON_LEFT):
          pinned = not pinned
          if pinned:
            rl.set_window_state(rl.ConfigFlags.FLAG_WINDOW_TOPMOST)
          else:
            rl.clear_window_state(rl.ConfigFlags.FLAG_WINDOW_TOPMOST)
      pin_col = PIN_ON if pinned else PIN_OFF
      tw = rl.measure_text_ex(font, "Top", 11, 0)
      rl.draw_text_ex(font, "Top", rl.Vector2(pin_rect.x + (pin_rect.width - tw.x) / 2,
                      pin_rect.y + (pin_rect.height - tw.y) / 2), 11, 0, pin_col)

    else:
      # Waiting state
      msg = "Waiting for replay..."
      tw  = rl.measure_text_ex(font, msg, 12)
      rl.draw_text_ex(font, msg, rl.Vector2((W - tw.x) / 2, H / 2 - 6), 12, 0, TXT_DIM)

    rl.end_drawing()

  rl.close_window()


if __name__ == "__main__":
  main()
