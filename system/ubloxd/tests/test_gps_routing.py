from types import SimpleNamespace

import pytest

from cereal import car, messaging
from openpilot.system.ubloxd import ubloxd


@pytest.mark.parametrize("brand,service", [("gm", "gpsLocation"), ("mock", "gpsLocationExternal")])
def test_main_routes_every_parsed_fix(monkeypatch, brand, service):
  cp = car.CarParams.new_message(brand=brand)
  monkeypatch.setattr(ubloxd, "Params", lambda: SimpleNamespace(get=lambda key: cp.to_bytes()))
  sent = []
  pm = SimpleNamespace(send=lambda service, message: sent.append((service, message)))
  monkeypatch.setattr(messaging, "PubMaster", lambda services: pm)
  monkeypatch.setattr(messaging, "sub_sock", lambda *args, **kwargs: None)
  # Several fixes in one receive cycle must all reach the publisher.
  incoming = iter([SimpleNamespace(ubloxRaw=b"", logMonoTime=1)])
  monkeypatch.setattr(messaging, "recv_one", lambda sock: next(incoming))
  parser = ubloxd.UbloxMsgParser(service)
  fixes = [messaging.new_message(service, valid=True) for _ in range(5)]
  monkeypatch.setattr(parser.framer, "add_data", lambda *args: range(5))
  monkeypatch.setattr(parser, "parse_frame", lambda index: (parser.gps_service, fixes[index]))
  def make_parser(actual_service):
    assert actual_service == service
    return parser
  monkeypatch.setattr(ubloxd, "UbloxMsgParser", make_parser)
  with pytest.raises(StopIteration):
    ubloxd.main()
  assert sent == [(service, fix) for fix in fixes]
