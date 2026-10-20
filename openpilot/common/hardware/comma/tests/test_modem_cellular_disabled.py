from unittest import mock

from openpilot.common.hardware.comma.modem import Modem, State


def _modem(params):
  m = Modem()
  m._read_param = lambda key: params.get(key, "")  # ty: ignore[invalid-assignment]  # test double
  m._publish_state = lambda **kw: m.S.update(kw)  # ty: ignore[invalid-assignment]  # test double
  m._atv = lambda cmd, pfx: '2,1' if cmd in ("AT+CREG?", "AT+CGREG?") else None  # ty: ignore[invalid-assignment]  # test double
  return m


def test_searching_dials_when_enabled():
  assert _modem({})._do_searching() == State.CONNECTING


def test_searching_does_not_dial_when_disabled():
  m = _modem({"CellularDisabled": "1"})
  assert m._do_searching() == State.SEARCHING
  assert m.S["registration"] == "home"


def test_connected_hangs_up_when_disabled():
  params = {}
  m = _modem(params)
  m._ppp = mock.MagicMock(has_exited=lambda: False)
  m._poll = lambda: None
  m._roaming_allowed = False  # as read during init
  with mock.patch("os.path.exists", return_value=True):
    assert m._do_connected() == State.CONNECTED
    params["CellularDisabled"] = "1"
    assert m._do_connected() == State.DISCONNECTING
