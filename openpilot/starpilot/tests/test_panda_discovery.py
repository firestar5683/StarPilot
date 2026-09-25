"""Exercise native discovery without touching Panda hardware."""

import subprocess
import sys
from pathlib import Path

import capnproto
import pytest

from openpilot.common.basedir import BASEDIR

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Native pandad discovery is tested on Linux")


@pytest.fixture(scope="module")
def discovery_binary(tmp_path_factory):
  directory = tmp_path_factory.mktemp("panda-discovery")
  source = directory / "discovery.cc"
  source.write_text('''
#include <cassert>
#include <string>
#include <vector>
#include "selfdrive/pandad/panda.h"

std::string model;
std::vector<std::string> usb_serials, spi_serials;
int spi_calls = 0;

namespace util {
std::string read_file(const std::string &path) {
  assert(path == "/sys/firmware/devicetree/base/model");
  return "comma " + model;
}
std::string strip(const std::string &text) { return text; }
}

std::vector<std::string> PandaUsbHandle::list() { return usb_serials; }
std::vector<std::string> PandaSpiHandle::list() {
  ++spi_calls;
  assert(model != "tici");  // C3's unused SPI interface must never be probed.
  return spi_serials;
}

int main(int argc, char **argv) {
  assert(argc == 3);
  model = argv[1];
  usb_serials = {"external-usb", "second-usb"};
  if (std::string(argv[2]) == "empty") usb_serials.clear();
  if (std::string(argv[2]) == "duplicate") usb_serials.push_back("internal-spi");
  assert(Panda::list() == usb_serials);
  spi_serials = {"internal-spi"};  // Internal SPI Panda becomes available later.
  auto expected = usb_serials;
  if (model != "tici" && std::string(argv[2]) != "duplicate") expected.push_back("internal-spi");
  assert(Panda::list() == expected);
  assert(spi_calls == (model == "tici" ? 0 : 2));
}
''')
  binary = directory / "discovery"
  root = Path(BASEDIR)
  includes = [root, root / "openpilot", root / "msgq_repo", root / "opendbc_repo",
              root / "openpilot/cereal/gen/cpp", capnproto.INCLUDE_DIR]
  subprocess.run([
    "c++", "-std=c++17", "-D__COMMA_HARDWARE__", "-ffunction-sections", "-fdata-sections",
    *[f"-I{path}" for path in includes], str(source), str(root / "openpilot/selfdrive/pandad/panda.cc"),
    "-Wl,--gc-sections", "-o", str(binary),
  ], check=True)
  return binary


@pytest.mark.parametrize("model", ["tici", "tizi", "mici"])
@pytest.mark.parametrize("inventory", ["multiple", "empty", "duplicate"])
def test_discovery_preserves_supported_transports(discovery_binary, model, inventory):
  subprocess.run([str(discovery_binary), model, inventory], check=True, timeout=5)
