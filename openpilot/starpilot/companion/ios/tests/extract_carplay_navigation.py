from pathlib import Path
import sys

source = Path("GalaxyBluetooth/CarPlaySceneDelegate.swift").read_text()
def method(name):
  start = source.index("    private func " + name + "(")
  opening = source.index("{", start)
  depth = 1
  end = opening + 1
  while depth:
    if source[end] == "{":
      depth += 1
    if source[end] == "}":
      depth -= 1
    end += 1
  return source[start:end].replace("private func", "func", 1)

stub = Path("tests/CarPlayNavigationRegression.swift").read_text()
Path(sys.argv[1]).write_text(stub.replace("__PRODUCTION_METHODS__", method("pushTemplate") + "\n" + method("popTemplate")))
