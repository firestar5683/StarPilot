"""Background authorization must not load the graphics/settings application."""
import subprocess
import sys


def test_configuration_authority_import_is_independent_of_ui():
  subprocess.run([sys.executable, '-c', '''
import sys
from openpilot.starpilot.galaxy.authority import LiveContextSource
assert LiveContextSource is not None
for name in ('pyray', 'numpy', 'PIL', 'openpilot.starpilot.galaxy.settings',
             'openpilot.starpilot.ui.feature_settings_owner'):
  assert name not in sys.modules, name
'''], check=True)
