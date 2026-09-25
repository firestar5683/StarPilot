#!/usr/bin/env python3
import argparse
import math
import os
import subprocess


def binary_files(filenames: list[str]) -> set[str]:
  if not filenames:
    return set()

  result = subprocess.run(
    ("git", "check-attr", "text", "-z", "--stdin"),
    input="\0".join(filenames),
    check=True,
    capture_output=True,
    text=True,
  )
  fields = result.stdout.rstrip("\0").split("\0") if result.stdout else []
  return {fields[i] for i in range(0, len(fields), 3) if fields[i + 2] == "unset"}


def check_added_large_files(filenames: list[str], max_kb: int) -> int:
  failed = False
  ignored = binary_files(filenames)
  for filename in filenames:
    with open(filename, 'rb') as file:
      if file.read(43).startswith(b'version https://git-lfs.github.com/spec/v1'):
        print(f'{filename}: placeholder pointer payload.')
        failed = True
        continue
    if os.stat(filename).st_size > 100 * 1024 * 1024:
      print(f'{filename}: ordinary Git blob exceeds 100 MiB.')
      failed = True
      continue
    if filename in ignored:
      continue

    size_kb = math.ceil(os.stat(filename).st_size / 1024)
    if size_kb > max_kb:
      print(f"{filename} ({size_kb} KB) exceeds {max_kb} KB.")
      failed = True

  return int(failed)


def main() -> int:
  parser = argparse.ArgumentParser(description="Check that tracked files do not exceed a size limit.")
  parser.add_argument("filenames", nargs="*")
  parser.add_argument("--maxkb", type=int, default=500, help="maximum allowable size in KiB")
  args = parser.parse_args()
  return check_added_large_files(args.filenames, args.maxkb)


if __name__ == "__main__":
  raise SystemExit(main())
