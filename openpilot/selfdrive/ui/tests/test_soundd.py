import threading
import numpy as np

from openpilot.common.test import OpenpilotTestCase
from openpilot.cereal import log, messaging
from openpilot.cereal.messaging import SubMaster, PubMaster
from openpilot.selfdrive.ui.soundd import SELFDRIVE_STATE_TIMEOUT, Soundd, check_selfdrive_timeout_alert

AudibleAlert = log.SelfdriveState.AudibleAlert


class TestSoundd(OpenpilotTestCase):
  def test_callback_defers_and_bounds_stream_status_logging(self, mocker):
    soundd = Soundd.__new__(Soundd)
    soundd.current_alert = AudibleAlert.none
    soundd.current_volume = 0.1
    soundd.loaded_sounds = {}
    soundd.saved_volumes = {}
    soundd.pending_stream_status = None
    soundd.stream_status_count = 0
    soundd.output_underflow_count = 0
    soundd.reported_output_underflows = 0
    soundd.stream_report_at = None
    soundd.last_callback_start_ns = None
    soundd.underflow_timing = None
    warning = mocker.patch("openpilot.selfdrive.ui.soundd.cloudlog.warning")
    error = mocker.patch("openpilot.selfdrive.ui.soundd.cloudlog.error")
    output = np.empty((8, 1), dtype=np.float32)

    soundd.callback(output, 8, None, "first underflow")
    soundd.callback(output, 8, None, "latest underflow")
    assert np.array_equal(output, np.zeros_like(output))
    warning.assert_not_called()
    error.assert_not_called()

    soundd.log_pending_stream_status()
    warning.assert_called_once_with("soundd stream diagnostics: status=latest underflow status_callbacks=2 output_underflows=0")
    soundd.log_pending_stream_status()
    warning.assert_called_once()
    error.assert_not_called()

  def test_check_selfdrive_timeout_alert(self, mocker):
    sm = SubMaster(['selfdriveState'])
    pm = PubMaster(['selfdriveState'])

    cs = messaging.new_message('selfdriveState')
    cs.selfdriveState.enabled = True
    threading.Timer(0.01, pm.send, args=("selfdriveState", cs)).start()
    sm.update(100)
    assert sm.updated['selfdriveState']

    sm.recv_time['selfdriveState'] = 0
    clock = mocker.patch("openpilot.selfdrive.ui.soundd.time.monotonic", return_value=SELFDRIVE_STATE_TIMEOUT)
    assert not check_selfdrive_timeout_alert(sm)

    clock.return_value = SELFDRIVE_STATE_TIMEOUT + 0.1
    assert check_selfdrive_timeout_alert(sm)

    clock.return_value = SELFDRIVE_STATE_TIMEOUT + 10
    assert not check_selfdrive_timeout_alert(sm)

  # TODO: add test with micd for checking that soundd actually outputs sounds
