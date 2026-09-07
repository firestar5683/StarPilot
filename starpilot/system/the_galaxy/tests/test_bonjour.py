from openpilot.starpilot.system.the_galaxy.bonjour import _service_label, _valid_ipv4


def test_bonjour_service_label_is_stable_and_dns_safe():
  assert _service_label("comma-ab_cd.example") == "StarPilot comma-ab-cd-example"
  assert _service_label("---") == "StarPilot comma"


def test_bonjour_only_advertises_non_loopback_ipv4_addresses():
  assert _valid_ipv4("192.168.50.22") == "192.168.50.22"
  assert _valid_ipv4("127.0.0.1") is None
  assert _valid_ipv4("fe80::1") is None
  assert _valid_ipv4(None) is None
