import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.release.release_files import release_files


class TestReleaseFiles(unittest.TestCase):
  def setUp(self):
    self.temp_dir = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp_dir.cleanup)
    self.root = Path(self.temp_dir.name)
    self.git("init", "--quiet")

  def git(self, *args: str, data: bytes | None = None) -> bytes:
    return subprocess.check_output(["git", *args], cwd=self.root, input=data, stderr=subprocess.PIPE)

  def track(self, name: str, contents: str = "source\n") -> Path:
    path = self.root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents)
    self.git("add", "--", name)
    return path

  def test_tracked_dependencies_and_special_paths(self):
    for path in ("panda/python/__init__.py", "msgq_repo/msgq/notes with spaces.txt", "upstream-sync.json"):
      self.track(path)
    script = self.track("panda/build.sh")
    script.chmod(0o755)
    self.git("add", "panda/build.sh")
    (self.root / "msgq").symlink_to("msgq_repo/msgq")
    self.git("add", "msgq")
    (self.root / "untracked.txt").write_text("not packaged\n")

    self.assertEqual(set(release_files(str(self.root))), {
      b"panda/python/__init__.py", b"msgq_repo/msgq/notes with spaces.txt",
      b"panda/build.sh", b"msgq", b"upstream-sync.json",
    })
    self.assertTrue(os.access(script, os.X_OK))

  def test_release_filters_and_optional_model(self):
    model = "openpilot/selfdrive/modeld/models/big_driving_tinygrad.pkl"
    for path in (model, ".lfsconfig", ".gitattributes", ".github/workflows/tests.yaml", "openpilot/main.py"):
      self.track(path)
    self.assertEqual(set(release_files(str(self.root))), {b".gitattributes", b"openpilot/main.py"})
    self.assertEqual(set(release_files(str(self.root), include_big_model=True)), {
      b".gitattributes", b"openpilot/main.py",
    })

  def test_gitlink_cannot_silently_omit_dependency(self):
    self.track("main.py")
    tree = self.git("write-tree").strip().decode()
    commit = self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                      "commit-tree", tree, "-m", "fixture").strip().decode()
    self.git("update-index", "--add", "--cacheinfo", f"160000,{commit},panda")
    with self.assertRaisesRegex(ValueError, "Cannot package gitlink: panda"):
      release_files(str(self.root))

  def test_prebuilt_replay_requires_tracked_runtime_outputs(self):
    source = Path(__file__).resolve().parents[3]
    for name in (".gitignore", "openpilot/tools/replay/.gitignore"):
      self.track(name, (source / name).read_text())
    self.track("openpilot/starpilot/replay/owner.py")
    self.assertIn(b"openpilot/starpilot/replay/owner.py", release_files(str(self.root)))
    self.track("prebuilt", "")
    for name in ("openpilot/tools/replay/replay", "openpilot/tools/replay/libmedia_mux.so"):
      with self.assertRaisesRegex(ValueError, "Prebuilt Replay Git package missing"):
        release_files(str(self.root))
      path = self.root / name
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_text("compiled runtime fixture\n")
      path.chmod(0o755)
      self.git("add", ".")
    selected = release_files(str(self.root))
    self.assertIn(b"openpilot/tools/replay/replay", selected)
    self.assertIn(b"openpilot/tools/replay/libmedia_mux.so", selected)
    (self.root / "openpilot/tools/replay/replay").chmod(0o644)
    self.git("add", ".")
    with self.assertRaisesRegex(ValueError, "invalid mode"):
      release_files(str(self.root))

  def test_unresolved_merge_cannot_be_packaged(self):
    self.track("main.py")
    blob = self.git("hash-object", "-w", "--stdin", data=b"conflict\n").strip().decode()
    self.git("update-index", "--index-info", data=f"100644 {blob} 2\tconflict.py\n".encode())
    with self.assertRaisesRegex(ValueError, "Cannot package unresolved merge: conflict.py"):
      release_files(str(self.root))


if __name__ == "__main__":
  unittest.main()
