import json
import os

import pytest
import requests

from openpilot.system.hardware.tici import agnos

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(TEST_DIR, "../agnos.json")


class FakeCloudlog:
  def info(self, *_args):
    pass

  def exception(self, *_args):
    pass


class TestAgnosUpdater:

  def test_manifest(self):
    with open(MANIFEST) as f:
      m = json.load(f)

    for img in m:
      content_lengths = set()
      for url in [img['url'], *img.get('fallback_urls', [])]:
        r = requests.head(url, timeout=10)
        r.raise_for_status()
        assert r.headers['Content-Type'] == "application/x-xz"
        content_lengths.add(r.headers.get('Content-Length'))

      assert len(content_lengths) == 1
      if not img['sparse']:
        assert img['hash'] == img['hash_raw']

  def test_download_url_uses_primary_for_first_three_attempts(self):
    partition = {
      "url": "https://primary/image.xz",
      "fallback_urls": ["https://fallback/image.xz"],
    }

    assert [agnos.get_partition_download_url(partition, i) for i in range(5)] == [
      "https://primary/image.xz",
      "https://primary/image.xz",
      "https://primary/image.xz",
      "https://fallback/image.xz",
      "https://fallback/image.xz",
    ]

  def test_network_failures_switch_to_fallback(self, monkeypatch, tmp_path):
    partition = {
      "name": "system",
      "url": "https://primary/image.xz",
      "fallback_urls": ["https://fallback/image.xz"],
    }
    manifest = tmp_path / "agnos.json"
    manifest.write_text(json.dumps([partition]))
    attempted_urls = []

    def flash_partition(_slot, attempted_partition, _cloudlog, _standalone):
      attempted_urls.append(attempted_partition['url'])
      if len(attempted_urls) <= agnos.PRIMARY_DOWNLOAD_ATTEMPTS:
        raise requests.exceptions.ReadTimeout()

    monkeypatch.setattr(agnos, "flash_partition", flash_partition)
    monkeypatch.setattr(agnos.os, "system", lambda *_args: 0)
    monkeypatch.setattr(agnos.time, "sleep", lambda *_args: None)

    agnos.flash_agnos_update(str(manifest), 1, FakeCloudlog())

    assert attempted_urls == [
      "https://primary/image.xz",
      "https://primary/image.xz",
      "https://primary/image.xz",
      "https://fallback/image.xz",
    ]

  def test_integrity_failures_do_not_switch_mirrors(self, monkeypatch, tmp_path):
    partition = {
      "name": "system",
      "url": "https://primary/image.xz",
      "fallback_urls": ["https://fallback/image.xz"],
    }
    manifest = tmp_path / "agnos.json"
    manifest.write_text(json.dumps([partition]))
    attempted_urls = []

    def flash_partition(_slot, attempted_partition, _cloudlog, _standalone):
      attempted_urls.append(attempted_partition['url'])
      raise ValueError("hash mismatch")

    monkeypatch.setattr(agnos, "flash_partition", flash_partition)
    monkeypatch.setattr(agnos.os, "system", lambda *_args: 0)

    with pytest.raises(ValueError, match="hash mismatch"):
      agnos.flash_agnos_update(str(manifest), 1, FakeCloudlog())

    assert attempted_urls == ["https://primary/image.xz"]
