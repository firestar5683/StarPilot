from pathlib import Path
import xml.etree.ElementTree as ET


ANDROID = "{http://schemas.android.com/apk/res/android}"
MANIFEST = Path(__file__).parents[1] / "android/app/src/main/AndroidManifest.xml"


def test_main_activity_handles_rotation_without_recreating_bluetooth_session():
  root = ET.parse(MANIFEST).getroot()
  activity = next(node for node in root.iter("activity") if node.get(ANDROID + "name") == ".MainActivity")
  changes = set(activity.get(ANDROID + "configChanges", "").split("|"))
  assert {"orientation", "screenSize", "screenLayout", "smallestScreenSize"} <= changes
