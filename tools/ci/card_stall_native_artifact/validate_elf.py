#!/usr/bin/env python3
"""Static, fail-closed comparison. Does not execute either shared library."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

BASELINE_SHA256 = '5a50085f727e3b22dcf596cb42be351066b0dcf7db7866fe04be40e69fe57133'


def command(*args):
  return subprocess.check_output(args, text=True)


def inspect(path):
  data = path.read_bytes()
  if len(data) < 64 or data[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<HH', data, 16) != (3, 183):
    raise ValueError(f'{path}: requires ELF64 little-endian AArch64 shared object')
  dynamic = command('readelf', '--wide', '-d', str(path))
  versions = command('readelf', '--wide', '--version-info', str(path))
  symbols = {}
  for line in command('nm', '-D', '--defined-only', '--format=posix', str(path)).splitlines():
    fields = line.split()
    if len(fields) >= 2:
      symbols[fields[0]] = fields[1]
  names = sorted(symbols)
  demangled = subprocess.check_output(['c++filt'], input='\n'.join(names)+'\n', text=True).splitlines()
  undefined = command('nm', '-D', '--undefined-only', '--format=posix', str(path))
  version_names = sorted(set(re.findall(r'Name: ([A-Za-z0-9_.]+)', versions)))
  return {
    'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data),
    'needed': sorted(re.findall(r'\(NEEDED\).*?\[(.*?)\]', dynamic)),
    'rpaths': re.findall(r'\((?:RUNPATH|RPATH)\).*?\[(.*?)\]', dynamic),
    'versions': version_names, 'defined_symbols': dict(zip(names, demangled, strict=True)),
    'undefined_symbols': undefined.splitlines(),
  }


def version_max(info, namespace):
  values = [tuple(map(int, name[len(namespace)+1:].split('.'))) for name in info['versions'] if re.fullmatch(re.escape(namespace)+r'_[0-9]+(?:\.[0-9]+)*', name)]
  return max(values, default=(0,))


def project_symbol(name):
  classes = r'(?:Context|Message|SubSocket|PubSocket|Poller|MSGQSubSocket|MSGQPoller|FakePoller|FakeSubSocket|SocketEventHandle|Event)'
  return bool(re.match(r'^(?:PyInit_ipc_pyx$|msgq_|messaging_use_fake\(|sigusr2_handler\(|event_state_shm_mmap\(|'
                       + classes+r'(?:::|<)|(?:typeinfo(?: name)?|vtable) for '+classes+r'(?:$|<))', name))


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--baseline', type=Path, required=True)
  parser.add_argument('--candidate', type=Path, required=True)
  parser.add_argument('--report', type=Path, required=True)
  args = parser.parse_args()
  baseline, candidate = inspect(args.baseline), inspect(args.candidate)
  errors = []
  if baseline['sha256'] != BASELINE_SHA256:
    errors.append('baseline hash does not match the reviewed e838 tracked artifact')
  unexpected = sorted(set(candidate['needed']) - set(baseline['needed']))
  if unexpected:
    errors.append(f'new dynamic dependencies: {unexpected}')
  # Standalone linking needs no runtime search path, so reject all rather than
  # maintaining a fragile allow-list of possible build-host paths.
  if candidate['rpaths']:
    errors.append(f'candidate must not embed RPATH/RUNPATH: {candidate["rpaths"]}')
  for namespace, ceiling in {'GLIBC': (2, 34), 'GLIBCXX': (3, 4, 32), 'CXXABI': version_max(baseline, 'CXXABI'), 'GCC': version_max(baseline, 'GCC')}.items():
    ceiling = min(ceiling, version_max(baseline, namespace))
    if version_max(candidate, namespace) > ceiling:
      errors.append(f'{namespace} requirement exceeds {ceiling}')
  nonnumeric_versions = [v for v in candidate['versions'] if not re.fullmatch(r'[A-Z][A-Z0-9]*_[0-9]+(?:\.[0-9]+)*', v)]
  if nonnumeric_versions:
    errors.append(f'unreviewed nonnumeric symbol versions: {nonnumeric_versions}')
  unexpected_versions = {v.split('_', 1)[0] for v in candidate['versions']} - {v.split('_', 1)[0] for v in baseline['versions']}
  if unexpected_versions:
    errors.append(f'new symbol-version namespace: {sorted(unexpected_versions)}')
  bsyms, csyms = baseline['defined_symbols'], candidate['defined_symbols']
  missing_project = {n: d for n, d in bsyms.items() if project_symbol(d) and n not in csyms}
  if missing_project:
    errors.append(f'missing existing msgq/extension exported symbols: {missing_project}')
  report = {
    'qualification': 'Static ABI boundary checks only; native tests and deployment review remain separate.',
    'baseline': baseline, 'candidate': candidate, 'errors': errors,
    'removed_exports': {n: bsyms[n] for n in sorted(set(bsyms)-set(csyms))},
    'added_exports': {n: csyms[n] for n in sorted(set(csyms)-set(bsyms))},
  }
  args.report.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
  if errors:
    raise SystemExit('\n'.join(errors))
  print('AArch64 ELF, dependency, search-path, symbol-version and existing msgq-export checks passed.')


if __name__ == '__main__':
  main()
