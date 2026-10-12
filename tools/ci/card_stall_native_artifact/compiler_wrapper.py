#!/usr/bin/env python3
"""Use only the preflight-approved GCC 13, recording effective ISA flags."""
import json
import os
from pathlib import Path
import sys

name = Path(sys.argv[0]).name
compiler = os.environ['ARM_CI_GXX' if name in ('g++', 'c++') else 'ARM_CI_GCC']
compatibility_flags = ['-fno-sized-deallocation'] if name in ('g++', 'c++') else []
command = [compiler, '-march=armv8-a', '-mtune=generic', *compatibility_flags, *sys.argv[1:]]
if any(flag == '-fsized-deallocation' or flag.startswith('-mcpu=') or (flag.startswith('-march=') and flag != '-march=armv8-a') or
       (flag.startswith('-mtune=') and flag != '-mtune=generic') for flag in sys.argv[1:]):
  raise SystemExit('CPU-specific compiler flags are prohibited for this artifact')
fd = os.open(os.environ['ARM_CI_COMPILER_LOG'], os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
try:
  os.write(fd, (json.dumps({'cwd': os.getcwd(), 'argv': command})+'\n').encode())
finally:
  os.close(fd)
os.execv(compiler, command)
