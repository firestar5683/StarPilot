import copy
import json
import pytest
from test_personality_profiles_api import _client, the_galaxy as server
from openpilot.starpilot.common.longitudinal_personality_profiles import default_personality_profiles, profile_document


def setup(monkeypatch, onroad=False):
  document = profile_document(default_personality_profiles(False), enabled=True)
  client, params = _client(monkeypatch, {'IsOnroad': onroad, 'IsOffroad': not onroad, 'CustomPersonalities': True,
                                        'LongitudinalPersonalityProfiles': json.dumps(document)})
  monkeypatch.setattr(server, '_get_toggle_backup_keys', lambda: {'CustomPersonalities'})
  monkeypatch.setattr(server.galaxy_backup, 'export_statistics', lambda path: {'schemaVersion': 1, 'drives': [], 'metrics': []})
  monkeypatch.setattr(server.utilities, 'stop_dashboard_background_analysis', lambda: None)
  monkeypatch.setattr(server.utilities, '_invalidate_dashboard_cache', lambda: None)
  captured = []
  monkeypatch.setattr(server.galaxy_backup, 'apply_restore', lambda *args: captured.append(args) or {'restoredCount': len(args[1]), 'addedDrives': 0, 'existingDrives': 0})
  return client, document, captured


def test_complete_export_and_restore_profile_document(monkeypatch):
  client, document, captured = setup(monkeypatch)
  response = client.post('/api/backup')
  assert response.status_code == 200, response.data
  data = json.loads(response.data)
  assert data['format'] == 'starpilot-backup'
  assert data['personalityProfiles'] == document
  assert data['settings']['CustomPersonalities'] is True
  response = client.post('/api/restore', json=data)
  assert response.status_code == 200, response.data
  assert captured[0][1]['LongitudinalPersonalityProfiles'] == document


@pytest.mark.parametrize('damage', ['profile', 'schema', 'missing_stats', 'secret', 'enabled'])
def test_invalid_backup_rejected_before_any_apply(monkeypatch, damage):
  client, document, captured = setup(monkeypatch)
  data = json.loads(client.post('/api/backup').data)
  if damage == 'profile': data['personalityProfiles']['profiles']['standard']['launchBoost'] = 'extreme'
  elif damage == 'schema': data['version'] = 9
  elif damage == 'missing_stats': del data['modelStatistics']
  elif damage == 'secret': data['history']['GithubSshKeys'] = 'x'
  elif damage == 'enabled': data['settings']['CustomPersonalities'] = False
  response = client.post('/api/restore', json=data)
  assert response.status_code == 400, response.data
  assert captured == []


def test_restore_requires_parked_state(monkeypatch):
  client, _, captured = setup(monkeypatch, onroad=True)
  data = json.loads(client.post('/api/backup').data)
  response = client.post('/api/restore', json=data)
  assert response.status_code == 400
  assert not captured
