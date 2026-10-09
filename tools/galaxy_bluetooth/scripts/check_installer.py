#!/usr/bin/env python3
"""Exercise the real installer with local wheels and unavailable ensurepip."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def check(wheelhouse, uv_bin=None):
    bridge = Path(__file__).resolve().parents[1] / "bridge"
    with tempfile.TemporaryDirectory(prefix="galaxy-install-") as scratch:
        root = Path(scratch)
        data = root / "data"
        blocker = root / "blocker"
        blocker.mkdir()
        (blocker / "ensurepip.py").write_text("raise RuntimeError('ensurepip is unavailable in this test')\n")
        env = dict(os.environ, GALAXY_BLE_PYTHON=sys.executable,
                   GALAXY_BLE_DATA_DIR=str(data), PYTHONPATH=str(blocker),
                   PATH=os.defpath, PIP_NO_INDEX="1", PIP_FIND_LINKS=str(wheelhouse),
                   PIP_NO_CACHE_DIR="1", UV_NO_INDEX="true", UV_FIND_LINKS=str(wheelhouse),
                   UV_NO_CONFIG="true", UV_CACHE_DIR=str(root / "uv-cache"))
        if uv_bin:
            env["PATH"] = str(uv_bin.parent) + os.pathsep + os.defpath
        else:
            # Model the partial environment left by the original failed install.
            subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(data / "venv")],
                           env=env, check=True, capture_output=True, text=True)
        command = ["/bin/sh", str(bridge / "install.sh")]
        first = subprocess.run(command, env=env, capture_output=True, text=True)
        if first.returncode:
            raise RuntimeError(first.stderr)
        key_file = data / "pairing.json"
        first_key = key_file.read_bytes()
        assert len(bytes.fromhex(json.loads(first_key)["key"])) == 32
        assert key_file.stat().st_mode & 0o077 == 0
        python = data / "venv/bin/python"
        subprocess.run([str(python), "-c",
                        "import dbus_next; from Crypto.Cipher import AES; "
                        "import importlib.util; assert importlib.util.find_spec('pip') is None"],
                       env=env, check=True, capture_output=True, text=True)
        second = subprocess.run(command, env=env, capture_output=True, text=True)
        if second.returncode:
            raise RuntimeError(second.stderr)
        assert key_file.read_bytes() == first_key
        assert "Existing pairing key preserved" in second.stdout
        print(f"{'uv' if uv_bin else 'pip'} installer: passed with ensurepip unavailable; dependencies isolated; key preserved")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheelhouse", type=Path, required=True,
                        help="Directory containing wheels for bridge/requirements.txt")
    parser.add_argument("--uv-bin", type=Path, help="Optional uv executable to also test")
    args = parser.parse_args()
    check(args.wheelhouse.resolve())
    if args.uv_bin:
        check(args.wheelhouse.resolve(), args.uv_bin.resolve())


if __name__ == "__main__":
    main()
