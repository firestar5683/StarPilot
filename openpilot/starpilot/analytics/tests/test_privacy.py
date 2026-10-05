import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from openpilot.starpilot.analytics.credentials import read_token
from openpilot.starpilot.analytics.location import coarse_cell, resolve_region


class TestCredentialProvisioning(unittest.TestCase):
  def test_only_private_regular_files_are_accepted(self):
    with tempfile.TemporaryDirectory() as root:
      token = Path(root) / 'token'
      token.write_text('provisioned-test-value\n')
      token.chmod(0o600)
      with patch.dict(os.environ, {'STARPILOT_STATS_TOKEN_FILE': str(token)}, clear=True):
        self.assertEqual(read_token(), 'provisioned-test-value')
        token.chmod(0o644)
        self.assertIsNone(read_token())
        token.chmod(0o600)
        link = Path(root) / 'link'
        link.symlink_to(token)
        os.environ['STARPILOT_STATS_TOKEN_FILE'] = str(link)
        self.assertIsNone(read_token())
        os.environ['STARPILOT_STATS_TOKEN_FILE'] = str(Path(root) / 'missing')
        self.assertIsNone(read_token())

  def test_invalid_environment_never_falls_back_or_becomes_a_header(self):
    for value in ('', 'short', 'credential\r\nInjected: yes', 'x' * 4097):
      with self.subTest(value=value[:8]), patch.dict(os.environ, {'STARPILOT_STATS_TOKEN': value}, clear=True):
        self.assertIsNone(read_token())
    with patch.dict(os.environ, {'STARPILOT_STATS_TOKEN': 'runtime-test-token'}, clear=True):
      self.assertEqual(read_token(), 'runtime-test-token')


class TestRegionalLocation(unittest.TestCase):
  @staticmethod
  def response(value):
    response = Mock(status_code=200)
    response.iter_content.return_value = (json.dumps(value).encode(),)
    return response

  def test_exact_gps_never_leaves_device_and_city_centroid_is_reported(self):
    session = Mock()
    reverse = self.response({'address': {'state': 'Example State', 'country': 'Example Country'}})
    city = self.response([{'lat': '42.1', 'lon': '-87.8', 'extratags': {'population': '150,000'},
                          'address': {'city': 'Example City'}}])
    session.get.side_effect = (reverse, city)
    result = resolve_region({'latitude': 41.88743, 'longitude': -87.64519}, session=session)
    params = session.get.call_args_list[0].kwargs['params']
    self.assertEqual((params['lat'], params['lon']), (42.0, -88.0))
    self.assertEqual(result, {'latitude': 42.1, 'longitude': -87.8, 'city': 'Example City',
                              'state': 'Example State', 'country': 'Example Country'})
    for call in session.get.call_args_list:
      self.assertFalse(call.kwargs['allow_redirects'])
      self.assertTrue(call.kwargs['stream'])
      self.assertNotIn('41.88743', str(call))
      self.assertNotIn('-87.64519', str(call))
    reverse.close.assert_called_once()
    city.close.assert_called_once()

  def test_invalid_fix_no_consent_or_drive_transition_prevents_lookups(self):
    session = Mock()
    for gps in (None, {}, {'latitude': float('nan'), 'longitude': 0}, {'latitude': 91, 'longitude': 0}):
      self.assertIsNone(coarse_cell(gps))
      resolve_region(gps, session=session)
    self.assertEqual(coarse_cell({'latitude': 0, 'longitude': 0}), (0.0, 0.0))
    resolve_region({'latitude': 40, 'longitude': -80}, session=session, allowed=lambda: False)
    session.get.assert_not_called()
    response = self.response({'address': {'country': 'Example'}})
    session.get.return_value = response
    gate = iter((True, True, False))
    result = resolve_region({'latitude': 40.2, 'longitude': -80.3}, session=session, allowed=lambda: next(gate))
    self.assertEqual(session.get.call_count, 1)
    self.assertEqual(result['latitude'], 40)
    self.assertEqual(result['country'], 'Example')

  def test_oversized_or_redirected_response_stops_at_bound(self):
    session = Mock()
    response = Mock(status_code=200)
    response.iter_content.return_value = iter((b'X' * 262145, b'NEVER READ'))
    session.get.return_value = response
    result = resolve_region({'latitude': 30.4, 'longitude': -90.1}, session=session)
    self.assertEqual(result['city'], 'N/A')
    self.assertEqual(next(response.iter_content.return_value), b'NEVER READ')
    response.close.assert_called_once()
    session.get.return_value = Mock(status_code=302)
    result = resolve_region({'latitude': 30.4, 'longitude': -90.1}, session=session)
    self.assertEqual(result['latitude'], 30)
    session.get.return_value.iter_content.assert_not_called()
