#!/usr/bin/env python3
"""Static, fail-closed comparison. Does not execute either shared library."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

BASELINE_EXECUTABLE_SHA256 = '03e06bcb9c70999be2031d5e36b95413287392cad3fe03aee68b3aee25ce6129'
LOADER_NAME = 'ld-linux-aarch64.so.1'
LOADER_PATH = '/lib/ld-linux-aarch64.so.1'
LOADER_ABI_SOURCE = 'https://sourceware.org/git/?p=glibc.git;a=blob;f=sysdeps/unix/sysv/linux/aarch64/ld.abilist;hb=glibc-2.34'

BASELINE_SHA256 = '5a50085f727e3b22dcf596cb42be351066b0dcf7db7866fe04be40e69fe57133'


def command(*args):
  return subprocess.check_output(args, text=True)


def dynamic_symbols(path):
  result = []
  for line in command('readelf', '--wide', '--dyn-syms', str(path)).splitlines():
    match = re.match(r'\s*\d+:\s+[0-9a-fA-F]+\s+(\d+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\S+)(?:\s+\((\d+)\))?', line)
    if match:
      size, kind, binding, visibility, section, name, version_index = match.groups()
      result.append({'size': int(size), 'kind': kind, 'binding': binding, 'visibility': visibility,
                     'section': section, 'name': name, 'version_index': int(version_index) if version_index else None})
  return result


def version_providers(versions):
  providers = {}
  provider = None
  in_needs = False
  for line in versions.splitlines():
    if line.startswith('Version needs section'):
      in_needs = True
    elif line.startswith('Version ') and 'section' in line:
      in_needs = False
    if not in_needs:
      continue
    match = re.search(r'File: (\S+)', line)
    if match:
      provider = match.group(1)
    match = re.search(r'Name: (\S+).*?Version: (\d+)', line)
    if match:
      providers[int(match.group(2))] = {'provider': provider, 'version': match.group(1)}
  return providers


def loader_exception(candidate, baseline_executable, runtime_loader):
  evidence = {'status': 'rejected', 'upstream_abi_source': LOADER_ABI_SOURCE,
              'upstream_abi_entry': 'GLIBC_2.17 __stack_chk_guard D 0x8',
              'target_loader_binary_inspected': False}
  errors = []
  needed_versions = {p['version'] for p in candidate['version_providers'].values() if p['provider'] == LOADER_NAME}
  if needed_versions != {'GLIBC_2.17'}:
    errors.append(f'loader version-needs must be exactly GLIBC_2.17: {needed_versions}')
  imports = []
  for symbol in candidate['dynamic_symbols']:
    provider = candidate['version_providers'].get(symbol['version_index'])
    if symbol['section'] == 'UND' and provider and provider['provider'] == LOADER_NAME:
      imports.append(symbol)
  evidence['loader_imports'] = imports
  if len(imports) != 1 or imports[0]['name'] != '__stack_chk_guard@GLIBC_2.17' or imports[0]['kind'] != 'OBJECT' or imports[0]['binding'] != 'GLOBAL':
    errors.append('loader imports must be solely GLOBAL OBJECT __stack_chk_guard@GLIBC_2.17')
  if baseline_executable is None or not baseline_executable.is_file():
    errors.append('exact reviewed baseline executable is required for loader exception')
  else:
    data = baseline_executable.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    evidence['baseline_executable_sha256'] = digest
    if digest != BASELINE_EXECUTABLE_SHA256:
      errors.append('baseline executable hash differs from reviewed pandad')
    else:
      interp = re.findall(r'Requesting program interpreter: ([^\]]+)', command('readelf', '--wide', '-l', str(baseline_executable)))
      evidence['baseline_executable_pt_interp'] = interp
      if interp != [LOADER_PATH]:
        errors.append('reviewed baseline executable does not identify the exact loader path')
  if not runtime_loader.is_file():
    errors.append('native CI runtime loader file is required for size/export check')
  else:
    data = runtime_loader.read_bytes()
    if len(data) < 64 or data[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<HH', data, 16) != (3, 183):
      errors.append('CI runtime loader is not an AArch64 ELF64 shared object')
    else:
      symbols = dynamic_symbols(runtime_loader)
      guards = [symbol for symbol in symbols if symbol['section'] != 'UND' and symbol['name'] == '__stack_chk_guard@@GLIBC_2.17']
      evidence['ci_loader'] = {'path': str(runtime_loader), 'sha256': hashlib.sha256(data).hexdigest(), 'guard_exports': guards}
      if len(guards) != 1 or guards[0]['size'] != 8 or guards[0]['kind'] != 'OBJECT' or guards[0]['binding'] != 'GLOBAL':
        errors.append('CI loader must export GLOBAL OBJECT __stack_chk_guard@@GLIBC_2.17 of size 8')
      exported_names = {symbol['name'].split('@')[0] for symbol in symbols if symbol['section'] != 'UND'}
      unversioned_loader_imports = [symbol['name'] for symbol in candidate['dynamic_symbols']
                                    if symbol['section'] == 'UND' and symbol['version_index'] is None and symbol['name'] in exported_names]
      if unversioned_loader_imports:
        errors.append(f'unversioned imports also matching loader exports are not approved: {unversioned_loader_imports}')
  if not errors:
    evidence['status'] = 'approved_exact_stack_guard_dependency'
  evidence['errors'] = errors
  return evidence


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
    'version_providers': version_providers(versions), 'dynamic_symbols': dynamic_symbols(path),
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
  parser.add_argument('--baseline-executable', type=Path)
  parser.add_argument('--runtime-loader', type=Path, default=Path(LOADER_PATH))
  args = parser.parse_args()
  baseline, candidate = inspect(args.baseline), inspect(args.candidate)
  errors = []
  if baseline['sha256'] != BASELINE_SHA256:
    errors.append('baseline hash does not match the reviewed e838 tracked artifact')
  unexpected = sorted(set(candidate['needed']) - set(baseline['needed']))
  loader_evidence = None
  if LOADER_NAME in unexpected:
    loader_evidence = loader_exception(candidate, args.baseline_executable, args.runtime_loader)
    if not loader_evidence['errors']:
      unexpected.remove(LOADER_NAME)
    else:
      errors.extend(loader_evidence['errors'])
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
    'baseline': baseline, 'candidate': candidate, 'errors': errors, 'loader_exception': loader_evidence,
    'removed_exports': {n: bsyms[n] for n in sorted(set(bsyms)-set(csyms))},
    'added_exports': {n: csyms[n] for n in sorted(set(csyms)-set(bsyms))},
  }
  args.report.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
  if errors:
    raise SystemExit('\n'.join(errors))
  print('AArch64 ELF, dependency, search-path, symbol-version and existing msgq-export checks passed.')


if __name__ == '__main__':
  main()
