"""Cloud tools never share credentials or OAuth across providers."""
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from openpilot.starpilot.connect.provider import PROVIDERS, OFFLINE
from openpilot.tools.lib import api, auth, auth_config
from openpilot.starpilot.galaxy.drive_history import recording_details


class TestCloudToolsIsolation(unittest.TestCase):
  def test_credentials_are_separate(self):
    with tempfile.TemporaryDirectory() as root, patch.object(auth_config.Paths, 'config_root', return_value=root):
      with patch.object(auth_config, 'active_provider', return_value=PROVIDERS['comma']):
        auth_config.set_token('comma-token')
      with patch.object(auth_config, 'active_provider', return_value=PROVIDERS['konik']):
        self.assertIsNone(auth_config.get_token())
        auth_config.set_token('konik-token')
        self.assertEqual(auth_config.get_token(), 'konik-token')
        auth_config.clear_token()
      with patch.object(auth_config, 'active_provider', return_value=PROVIDERS['comma']):
        self.assertEqual(auth_config.get_token(), 'comma-token')

  def test_offline_and_oauth_denied_before_network(self):
    with patch.object(api, 'active_provider', return_value=OFFLINE), patch.object(api.requests, 'Session') as session:
      with self.assertRaises(api.APIError):
        api.CommaApi('secret')
      session.assert_not_called()
    with patch.object(auth, 'active_provider', return_value=PROVIDERS['konik']):
      with self.assertRaises(ValueError):
        auth.auth_redirect_link('github', 1234)
      self.assertIn('api.konik.ai/v2/user/token', auth.login('github')['error'])

  def test_pinned_host_and_http_rejection(self):
    with patch.object(api, 'active_provider', return_value=PROVIDERS['konik']):
      client = api.CommaApi('konik-token')
      self.assertEqual(client.api_host, 'https://api.konik.ai')
      response = MagicMock(status_code=401)
      response.__enter__.return_value = response
      client.session.request = MagicMock(return_value=response)
      with self.assertRaises(api.UnauthorizedError):
        client.get('v1/me')
      response.json.assert_not_called()
    with patch.object(api, 'active_provider', return_value=PROVIDERS['comma']):
      with self.assertRaises(api.APIError):
        client.get('v1/me')
    client.session.request.assert_called_once()


class TestRecordingCloudLinks(unittest.TestCase):
  def test_recording_provider_not_active_provider(self):
    routes = {'routes': [{'routeId': '2026-10-01--12-00-00', 'provider': name} for name in ('comma', 'konik', None)]}
    result = recording_details(routes, {}, None, device_ids={'comma': '0123456789abcdef', 'konik': 'fedcba9876543210'})
    self.assertTrue(result['routes'][0]['connectUrl'].startswith('https://connect.comma.ai/'))
    self.assertTrue(result['routes'][1]['connectUrl'].startswith('https://stable.konik.ai/'))
    self.assertIsNone(result['routes'][2]['connectUrl'])

  def test_legacy_is_comma_and_unknown_identity_has_no_link(self):
    result = recording_details({'routes': [{'routeId': '2026-10-01--12-00-00'}]}, {}, '0123456789abcdef')
    self.assertTrue(result['routes'][0]['connectUrl'].startswith('https://connect.comma.ai/'))
    result = recording_details({'routes': [{'routeId': '2026-10-01--12-00-00', 'provider': 'konik'}]}, {}, '0123456789abcdef')
    self.assertIsNone(result['routes'][0]['connectUrl'])
