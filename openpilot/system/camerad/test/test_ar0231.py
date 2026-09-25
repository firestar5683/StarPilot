"""Legacy sensor exposure and BPS configuration without camera hardware."""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
CAMERA = ROOT / 'openpilot/system/camerad'


def function(text, name):
  start = text.index('{', text.index(name))
  depth = 0
  for end in range(start, len(text)):
    depth += (text[end] == '{') - (text[end] == '}')
    if depth == 0:
      return text[start:end + 1]
  raise AssertionError(name)


class TestAR0231(unittest.TestCase):
  def test_disabled_sensor_releases_session_after_configuration(self):
    source = (CAMERA / 'cameras/spectra.cc').read_text()
    camera_open = function(source, 'void SpectraCamera::camera_open(')
    disabled = function(camera_open, 'if (!enabled)')
    self.assertEqual(re.findall(r'\b(camera_close|return)\b', disabled), ['camera_close', 'return'])
    self.assertLess(camera_open.index('openSensor()'), camera_open.index('if (!enabled)'))
    self.assertLess(camera_open.index('if (!enabled)'), camera_open.index('buf.init('))
    close = function(source, 'void SpectraCamera::camera_close()')
    enabled = function(close, 'if (enabled)')
    self.assertNotIn('CAM_RELEASE_DEV, session_handle, sensor_dev_handle', enabled)
    self.assertIn('CAM_RELEASE_DEV, session_handle, sensor_dev_handle', close)
    self.assertIn('CAM_REQ_MGR_DESTROY_SESSION', close)

  def test_build_and_probe_preserve_modern_priority(self):
    source = (CAMERA / 'cameras/spectra.cc').read_text()
    probe = function(source, 'bool SpectraCamera::openSensor()')
    self.assertEqual(re.findall(r'init_sensor_lambda\(new (\w+)\)', probe), ['OS04C10', 'OX03C10', 'AR0231'])
    self.assertIn("'sensors/ar0231.cc'", (CAMERA / 'SConscript').read_text())
    for row in ('bps_cfg', 'bps_striping_output', 'bps_settings'):
      text = (CAMERA / 'cameras/bps_blobs.h').read_text()
      rows = re.findall(r'\{([^{}]*)\}', function(text, row))
      self.assertEqual(len(rows), 4)
      self.assertEqual(len(re.findall(r'0x[0-9a-fA-F]+', rows[1])), {'bps_cfg':768, 'bps_striping_output':2464, 'bps_settings':684}[row])

  def test_actual_sensor_exposure_and_bps_contract(self):
    compiler = shutil.which('clang++') or shutil.which('g++')
    if compiler is None:
      self.skipTest('C++ compiler unavailable')
    source = (CAMERA / 'cameras/spectra.cc').read_text()
    bps = function(source, 'void SpectraCamera::config_bps(')
    icp = function(source, 'void SpectraCamera::configICP()')
    def match(pattern, source, flags=0):
      found = re.search(pattern, source, flags)
      assert found is not None
      return found[1]

    downscale = match(r'bool needs_downscale = ([^;]+);', bps)
    patches = match(r'int num_patches = ([^;]+);', bps)
    cycles = match(r'tmp.clk.frame_cycles = ([^;]+);', bps)
    striping = match(r'uint32_t striping_size = ([^;]+);', icp)
    striping_bl = match(r'bps_cdm_striping_bl.init\(m, ([^,]+),', icp)
    legacy = function(source, 'static bool uses_legacy_bps_config')
    knees = function(bps, 'if (legacy_bps)')
    probe = function(source, 'bool SpectraCamera::openSensor()')
    condition = match(r'if \((!init_sensor_lambda\(new OS04C10\).*?)\) \{', probe, re.S)
    for name, identity in (('OS04C10', 3), ('OX03C10', 2), ('AR0231', 1)):
      condition = condition.replace('new ' + name, str(identity))
    with tempfile.TemporaryDirectory(prefix='camera-sensor-contract-') as directory:
      root = Path(directory)
      for path, text in {
        'media/cam_isp.h': '#pragma once\n#define CAM_ISP_PATTERN_BAYER_GRGRGR 0\n#define CAM_FORMAT_MIPI_RAW_12 12\n',
        'media/cam_sensor.h': '#pragma once\n#include <cstdint>\nstruct i2c_random_wr_payload {uint32_t reg_addr; uint32_t reg_data;};\n',
        'openpilot/cereal/gen/cpp/log.capnp.h': ('#pragma once\nnamespace cereal {struct FrameData ' +
                                               '{enum class ImageSensor {UNKNOWN, AR0231, OX03C10, OS04C10};};}\n'),
      }.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
      test = root / 'sensor.cc'
      test.write_text('''#include <cassert>
#include <cmath>
#include <memory>
#include "system/camerad/sensors/sensor.h"
#include "system/camerad/cameras/bps_blobs.h"
static bool uses_legacy_bps_config(const SensorInfo *sensor) ''' + legacy + '''
int main() {
  AR0231 ar;
  assert(ar.frame_width == 1928 && ar.frame_height == 1208 && ar.frame_stride == 2896);
  assert(ar.extra_height == 12 && ar.frame_offset == 2 && ar.stats_offset == 1210);
  assert(ar.probe_reg_addr == 0x3000 && ar.probe_expected_data == 0x354);
  assert(ar.mclk_frequency == 19200000 && ar.readout_time_ns == 22850000);
  for (int port=0; port<3; ++port) assert(ar.getSlaveAddress(port) == (port==1 ? 0x30 : 0x20));
  for (int gain=1; gain<=13; ++gain) for (int exposure : {2, 32, 2133}) for (bool dc : {false,true}) {
    auto values = ar.getExposureRegisters(exposure, gain, dc);
    assert(values.size() == 3);
    assert(values[0].reg_addr == 0x3366 && values[0].reg_data == (0xff00U | (gain << 4) | gain));
    assert(values[1].reg_addr == 0x3362 && values[1].reg_data == unsigned(dc));
    assert(values[2].reg_addr == 0x3012 && values[2].reg_data == unsigned(exposure));
  }
  assert(ar.getExposureScore(10,10,6,1,6)==0);
  assert(std::abs(ar.getExposureScore(10,10,7,1,6)-5.6f)<0.00001f);
  assert(std::abs(ar.getExposureScore(10,10,5,1,6)-0.21f)<0.00001f);
  assert(ar.getExposureScore(12,10,6,1,6)==20);
  assert(ar.linearization_lut.size()==36 && ar.gamma_lut_rgb.size()==64 && ar.vignetting_lut.size()==221);
  {
    auto sensor=std::make_unique<AR0231>();
    std::vector<uint32_t> bps_lin_reg;
''' + knees + '''
    assert((bps_lin_reg == std::vector<uint32_t>{0x0bff07ff,0x1bff17ff,0x3fff23ff,0x3fff3fff}));
  }
  for (int success : {0,1,2,3}) {
    std::vector<int> called;
    auto init_sensor_lambda=[&](int identity) {called.push_back(identity); return identity==success;};
    bool failed=''' + condition + ''';
    assert(failed == (success==0));
    assert((called == (success==3 ? std::vector<int>{3} : success==2 ? std::vector<int>{3,2} : std::vector<int>{3,2,1})));
  }
  for (auto identity : {cereal::FrameData::ImageSensor::AR0231, cereal::FrameData::ImageSensor::OX03C10, cereal::FrameData::ImageSensor::OS04C10}) {
    for (int scale : {1,2}) {
      auto sensor = std::make_unique<SensorInfo>(); sensor->image_sensor=identity; sensor->out_scale=scale;
      bool legacy_bps=uses_legacy_bps_config(sensor.get());
      bool needs_downscale=''' + downscale + ''';
      int num_patches=''' + patches + ''';
      int frame_cycles=''' + cycles + ''';
      unsigned striping_size=''' + striping + ''';
      unsigned striping_bl=''' + striping_bl + ''';
      assert(needs_downscale == (!legacy_bps && scale>1));
      assert(num_patches == (legacy_bps ? 9 : scale>1 ? 14 : 12));
      assert(frame_cycles == (legacy_bps ? 2329024 : 20000000));
      assert(striping_size == (legacy_bps ? 2464 : 3160));
      assert(striping_bl == (legacy_bps ? 41216 : 53216));
    }
  }
}
''')
      artifact = root / 'sensor-test'
      result = subprocess.run([compiler, '-std=gnu++17', '-I', str(root), '-I', str(ROOT / 'openpilot'),
                               str(CAMERA / 'sensors/ar0231.cc'), str(test), '-o', str(artifact)],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
      self.assertEqual(result.returncode, 0, result.stdout)
      subprocess.run([str(artifact)], check=True)


if __name__ == '__main__':
  unittest.main()
