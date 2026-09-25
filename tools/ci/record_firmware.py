#!/usr/bin/env python3
"""Record firmware build commands/artifacts without installing or flashing them."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.ci.run_vehicle_tests import ROOT, sha256, source_provenance


def compile_commands(text, variant):
  commands = []
  for line in text.splitlines():
    if "arm-none-eabi-gcc" not in line:
      continue
    command = shlex.split(line)
    if "-c" in command and any(token.endswith("board/main.c") for token in command):
      commands.append(command)
  if not commands:
    raise ValueError("Build log has no actual Panda main compilation command")
  if any(("-DALLOW_DEBUG" in command) != (variant == "debug") for command in commands):
    raise ValueError("Panda compiled flags do not match the requested variant")
  return commands


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--variant", choices=("debug", "release"), required=True)
  parser.add_argument("--build-log", type=Path, required=True)
  parser.add_argument("--output", type=Path, required=True)
  args = parser.parse_args()
  commands = compile_commands(args.build_log.read_text(), args.variant)
  files = [ROOT / "panda/board/obj" / name for name in (
    "panda.bin.signed", "panda/main.elf", "bootstub.panda.bin",
    "panda_h7.bin.signed", "panda_h7/main.elf", "bootstub.panda_h7.bin", "version")]
  version = files[-1].read_text()
  if f"-{args.variant.upper()}" not in version:
    raise ValueError("Panda version stamp does not match the compiled variant")
  report = {"schema_version": 1, "variant": args.variant, "source": source_provenance(), "commands": commands,
            "compiler_version": subprocess.check_output(["arm-none-eabi-gcc", "--version"], text=True),
            "artifacts": {str(path.relative_to(ROOT)): sha256(path) for path in files},
            "version_stamp": version, "build_log_sha256": sha256(args.build_log),
            "certificate": "checked-in development certificate, including the RELEASE build",
            "certificate_sha256": sha256(ROOT / "panda/board/crypto/certs/debug"),
            "scope": "compile/link only; no release-key signing, flashing, device execution, or firmware compatibility qualification"}
  args.output.parent.mkdir(parents=True, exist_ok=True)
  args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
  main()
