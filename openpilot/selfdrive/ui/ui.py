#!/usr/bin/env python3
import os
import sys

from openpilot.cereal import messaging
from openpilot.common.hardware import COMMA_HARDWARE, HARDWARE
from openpilot.common.realtime import Priority, config_realtime_process, drop_realtime, set_core_affinity
from openpilot.system.ui.lib.application import gui_app
from openpilot.selfdrive.ui.layouts.main import MainLayout
from openpilot.selfdrive.ui.mici.layouts.main import MiciMainLayout
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.startup import select_ui

BIG_UI = gui_app.big_ui()


def update_frame(preview=None, controllers=None):
  gui_app.measure_frame_phase("ui_state", ui_state.update)
  if controllers is not None:
    gui_app.measure_frame_phase("controllers", controllers.poll)
  if preview is not None:
    preview.poll()


def main():
  c4 = COMMA_HARDWARE and HARDWARE.get_device_type() == "mici"
  cores = {6} if c4 else {5}
  main_thread_configured = False
  config_realtime_process(0, Priority.UI)

  selection = select_ui(Profile.LARGE if BIG_UI else Profile.COMPACT, os.environ)
  print(f"UI: {'StarPilot' if selection.custom else 'upstream'} selected ({selection.reason})", file=sys.stderr, flush=True)
  star_ui = selection.custom
  gui_app.init_window("UI")
  if star_ui:
    from openpilot.starpilot.ui.runtime_app import StarMainLayout, StarMiciMainLayout
    from openpilot.starpilot.ui.layout_preview_runtime import LayoutPreviewRuntime
    layout = StarMainLayout() if BIG_UI else StarMiciMainLayout()
    from openpilot.starpilot.controllers.runtime import ControllerRuntime
    from openpilot.starpilot.galaxy.settings import LiveContextSource
    # Both runtimes read the UI collector; neither advances or closes its sockets.
    controller_authority = LiveContextSource(ui_state.params, messages=ui_state.sm,
                                             borrowed_messages=True, evidence_wait_ms=0)
    preview_authority = LiveContextSource(ui_state.params, messages=ui_state.sm,
                                          borrowed_messages=True, evidence_wait_ms=0)
    controllers = ControllerRuntime(ui_state.params, actions=layout.star._favorite_actions,
                                    favorites=layout.star.favorites_owner.snapshot,
                                    invoke_favorite=layout.star.favorites_owner.invoke, authority=controller_authority)
    preview = LayoutPreviewRuntime(ui_state.params, (Profile.LARGE if BIG_UI else Profile.COMPACT).value,
                                   offroad_hint=ui_state.is_offroad, authority=preview_authority)
  else:
    layout = MainLayout() if BIG_UI else MiciMainLayout()
    preview = None
    controllers = None

  pm = messaging.PubMaster(['uiDebug'])
  try:
    for should_render, frame_time, cpu_time in gui_app.render(before_frame=lambda: update_frame(preview, controllers)):
      if should_render:
        if c4 and not main_thread_configured:
          # Share the camera core with normal scheduling, without FIFO display
          # work preempting camera work or waiting on the driving core.
          drop_realtime()
          os.setpriority(os.PRIO_PROCESS, 0, 0)
          if os.sched_getscheduler(0) != os.SCHED_OTHER or os.getpriority(os.PRIO_PROCESS, 0) != 0:
            raise RuntimeError("Could not configure display scheduling")
          main_thread_configured = True
        # reaffine after power save offlines our core
        if COMMA_HARDWARE and os.sched_getaffinity(0) != cores:
          try:
            set_core_affinity(list(cores))
          except OSError:
            pass

        msg = messaging.new_message('uiDebug')
        msg.uiDebug.cpuTimeMillis = cpu_time * 1000
        msg.uiDebug.frameTimeMillis = frame_time * 1000
        pm.send('uiDebug', msg)
  finally:
    if star_ui:
      try:
        if preview is not None:
          preview.close()
      finally:
        try:
          controllers.close()
        finally:
          layout.close()


if __name__ == "__main__":
  main()
