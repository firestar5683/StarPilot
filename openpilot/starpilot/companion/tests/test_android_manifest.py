from pathlib import Path
import xml.etree.ElementTree as ET


ANDROID = "{http://schemas.android.com/apk/res/android}"
MANIFEST = Path(__file__).parents[1] / "android/app/src/main/AndroidManifest.xml"


def test_main_activity_handles_rotation_without_recreating_bluetooth_session():
  root = ET.parse(MANIFEST).getroot()
  activity = next(node for node in root.iter("activity") if node.get(ANDROID + "name") == ".MainActivity")
  changes = set(activity.get(ANDROID + "configChanges", "").split("|"))
  assert {"orientation", "screenSize", "screenLayout", "smallestScreenSize"} <= changes


def test_in_app_updater_has_scoped_install_permission_and_receiver():
  root = ET.parse(MANIFEST).getroot()
  permissions = {node.get(ANDROID + "name") for node in root.findall("uses-permission")}
  assert "android.permission.REQUEST_INSTALL_PACKAGES" in permissions
  receiver = next(node for node in root.iter("receiver") if node.get(ANDROID + "name") == ".AppInstallReceiver")
  assert receiver.get(ANDROID + "exported") == "false"
