import unittest

from openpilot.starpilot.bluetooth.uniden.protocol import parse_alerts, parse_telemetry, strongest, uniden_name


class UnidenProtocolTest(unittest.TestCase):
  def test_radar_and_laser_alerts(self):
    alerts = parse_alerts(b'1,7,KA,6,212,34.7,F,1,0&1,8,LASER,8,255,2,R,2,0&0&')
    self.assertEqual([alert.band for alert in alerts], ['KA', 'LASER'])
    ka, laser = alerts
    self.assertEqual((ka.strength, ka.frequency_ghz, ka.description, ka.direction_name), (6, 34.7, '34.7 GHz', 'front'))
    self.assertFalse(ka.is_muted)
    self.assertEqual((laser.laser_gun, laser.frequency_ghz, laser.direction_name, laser.mute_status), ('Stalker', None, 'rear', 'muted'))
    self.assertIs(strongest(alerts), laser)

  def test_inactive_and_out_of_band_alerts(self):
    self.assertEqual(parse_alerts('0'), [])
    self.assertEqual(parse_alerts('0,1,KA,5'), [])
    alerts = parse_alerts('1,2,RT3,4,100,,S,1,0')
    self.assertEqual(alerts[0].description, 'Gatso')
    self.assertIsNone(strongest(alerts))

  def test_telemetry(self):
    telemetry = parse_telemetry('13.9&1,450,45&N,61,700,C&0&12&on&3')
    self.assertEqual(telemetry.voltage, 13.9)
    self.assertEqual((telemetry.poi.kind, telemetry.poi.distance, telemetry.poi.speed_limit), ('1', 450, 45))
    self.assertTrue(telemetry.gps_locked)
    self.assertIsNone(telemetry.warning)
    self.assertEqual(parse_telemetry('').voltage, None)

  def test_advertised_names(self):
    self.assertTrue(uniden_name('R4W@01A2'))
    self.assertTrue(uniden_name('Uniden R9'))
    self.assertFalse(uniden_name('R4 Speaker'))


if __name__ == '__main__':
  unittest.main()
