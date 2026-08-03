from openpilot.selfdrive.ui.ui_state import ui_state


def restart_needed_callback(_):
  ui_state.ui_params.put_bool("OnroadCycleRequested", True)
