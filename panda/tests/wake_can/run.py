#!/usr/bin/env python3
"""Compile verbatim current C functions, not a Python decoder/power-policy model.
No SCons execution, firmware build, artifact signing, or device access.
"""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = 'bb04e935272ccbc7551dd5f46d18197757a35587'
FILES = ['panda/board/drivers/can_common.h', 'panda/board/main.c',
         'panda/board/drivers/bootkick.h', 'panda/board/boards/cuatro.h']


def between(text, start, end):
  assert text.count(start) == 1, start
  tail = text[text.index(start):]
  assert end in tail, end
  return tail[:tail.index(end)]


def generate(read):
  can, main, boot, cuatro = [read(p) for p in FILES]
  independent_wake = 'bool recent_heartbeat, bool wake)' in boot
  # Historical two-argument definitions must not include today's declaration.
  if not independent_wake:
    boot = boot.replace('#include "bootkick_declarations.h"', '')
  globals_ = between(can, 'bool ignition_can = false;', '\nbool can_silent')
  # Added wake globals immediately precede ignition globals in candidate.
  if 'bool wake_on_can = false;' in can:
    globals_ = between(can, 'bool wake_on_can = false;', '\nbool can_silent')
  else:
    globals_ = 'bool wake_on_can=false; uint32_t wake_on_can_cnt=0;\n' + globals_
  chunks = [
    ('can globals', globals_),
    ('decoder', between(can, 'void ignition_can_hook(CANPacket_t *msg) {', '\nbool can_tx_check_min_slots_free')),
    ('ignition line', between(main, 'static bool panda_ignition_line(void) {', '\n\n// ********************* Serial')),
    ('car safety predicate', between(main, 'bool is_car_safety_mode(uint16_t mode) {', '\n// ***************************** main')),
    ('cuatro GPIO callback', between(cuatro, 'static void cuatro_set_bootkick(BootState state) {', '\nstatic void cuatro_set_amp_enabled')),
    ('bootkick', boot),
    ('entire 8Hz tick', between(main, '#define HEARTBEAT_IGNITION_CNT_ON', '\nint main(void) {')),
  ]
  call = 'bootkick_tick(ign, hb, wake);' if independent_wake else '(void)wake; bootkick_tick(ign, hb);'
  adapter = '\nstatic void test_bootkick(bool ign, bool hb, bool wake) { ' + call + ' }\n'
  adapter += 'static void legacy_bootkick(bool ign, bool hb) { test_bootkick(ign, hb, false); }\n'
  output = '#include "fixture.h"\n' + '\n'.join(x[1] for x in chunks) + adapter + '\n#include "scenarios.h"\n'
  return output, {name: hashlib.sha256(text.encode()).hexdigest() for name, text in chunks}


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--evidence', type=Path, required=True)
  parser.add_argument('--red', action='store_true', help='Expect stock states assertion to fail')
  parser.add_argument('--base', default=BASE, help='Stock Git revision for parity checks')
  parser.add_argument('--regression-ref', help='Optional historical pre-fix Git revision; expect DRIVE wake failure')
  args = parser.parse_args()
  args.evidence.mkdir(parents=True, exist_ok=True)
  source, hashes = generate(lambda p: (ROOT / p).read_text())
  if args.regression_ref:
    source, hashes = generate(lambda p: subprocess.check_output(['git', 'show', f'{args.regression_ref}:{p}'], cwd=ROOT, text=True))
  stock, stock_hashes = generate(lambda p: subprocess.check_output(['git', 'show', f'{args.base}:{p}'], cwd=ROOT, text=True))
  (args.evidence / 'candidate.c').write_text(source)
  (args.evidence / 'stock.c').write_text(stock)
  tested_files = FILES + ['panda/board/drivers/can_common_declarations.h',
                         'panda/board/drivers/bootkick_declarations.h',
                         'panda/board/boards/board_declarations.h',
                         'opendbc_repo/opendbc/safety/can.h']
  tested_files += [str(p.relative_to(ROOT)) for p in sorted(HERE.iterdir()) if p.suffix in {'.py', '.h', '.md'}]
  manifest = {'base': args.base, 'source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in tested_files},
              'extracted_sha256': hashes, 'stock_extracted_sha256': stock_hashes, 'runs': []}
  scenarios = ['states','invalid','stale','watchdog','drive_watchdog','boot','serial','gpio','existing','other_cars','drive_edge',
               'independent_edges','wake_reset','stock_drive']
  for tesla, hkg, gm, ignore in itertools.product([False, True], repeat=4):
    for debug, allow_debug in [(False,False), (True,True), (False,True)]:
      variant = f'tesla{int(tesla)}-hkg{int(hkg)}-gm{int(gm)}-ignore{int(ignore)}-debug{int(debug)}-allow{int(allow_debug)}'
      flags = [f'-D{x}' for x, yes in [('PANDA_TESLA_WAKE_ON_CAN',tesla),('PANDA_HKG_REMOTE_START',hkg),('PANDA_GM_REMOTE_START_C9',gm),
               ('PANDA_IGNORE_IGNITION_LINE',ignore),('DEBUG',debug),('ALLOW_DEBUG',allow_debug)] if yes]
      binaries = {}
      for name in ['candidate', 'stock']:
        binary = args.evidence / f'{name}-{variant}'
        command = [os.environ.get('CC','cc'), '-std=gnu11', '-Wall','-Wextra','-Werror',
                   '-Wno-sign-compare', '-O2','-g','-fsanitize=undefined','-fno-sanitize-recover=all',
                   *flags, '-I'+str(HERE), '-I'+str(ROOT/'panda'), '-I'+str(ROOT/'panda/board/drivers'),
                   '-I'+str(ROOT/'opendbc_repo'), str(args.evidence/f'{name}.c'), '-o', str(binary)]
        subprocess.run(command, check=True)
        binaries[name] = binary
        manifest['runs'].append({'compile': command})
      if args.regression_ref:
        run = subprocess.run([str(binaries['candidate']), 'drive_edge'], text=True, capture_output=True)
        assert run.returncode != 0 and 'observed_boot==BOOT_BOOTKICK' in run.stderr, run.stderr
        manifest['runs'].append({'variant':variant,'regression_red_rc':run.returncode,'stderr':run.stderr})
        (args.evidence/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print('RED verified: pre-fix candidate masks DRIVE:', run.stderr.strip())
        return
      if args.red:
        run = subprocess.run([str(binaries['stock']), 'states'], text=True, capture_output=True)
        assert run.returncode != 0 and 'wake_on_can == (state != 0)' in run.stderr, run.stderr
        print('RED verified: stock fails non-OFF wake assertion:', run.stderr.strip())
        return
      selected = scenarios + ['checksum'] if tesla else [
        'disabled', 'drive_watchdog', 'boot', 'serial', 'gpio', 'existing', 'other_cars',
        'stock_drive', 'independent_edges', 'wake_reset']
      for scenario in selected:
        run = subprocess.run([str(binaries['candidate']),scenario], text=True,capture_output=True)
        manifest['runs'].append({'variant':variant,'scenario':scenario,'rc':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
        if run.returncode:
          print(variant, scenario, run.stdout, run.stderr)
          raise SystemExit(run.returncode)
      subprocess.run([str(binaries['stock']), 'stock_drive'], check=True)
      boot_traces = [subprocess.check_output([str(binaries[name]),'boot_trace']) for name in ['candidate','stock']]
      assert boot_traces[0] == boot_traces[1], f'Boot/reset/harness parity failed: {variant}'
      (args.evidence / f'boot-parity-{variant}.txt').write_bytes(boot_traces[0])
      manifest['runs'].append({'variant':variant,'boot_parity_frames':20000,'sha256':hashlib.sha256(boot_traces[0]).hexdigest()})
      traces = [subprocess.check_output([str(binaries[name]),'trace']) for name in ['candidate','stock']]
      assert traces[0] == traces[1], f'Ignition/watchdog parity failed: {variant}'
      trace_hash = hashlib.sha256(traces[0]).hexdigest()
      (args.evidence / f'parity-{variant}.txt').write_bytes(traces[0])
      manifest['runs'].append({'variant':variant,'parity_frames':20000,'sha256':trace_hash})
      print(f'PASS {variant}: {len(selected)} scenarios; 20000-frame ignition/watchdog and boot/reset stock parity; DRIVE edge preserved')
  (args.evidence/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
  summary = {'configurations':sum('parity_frames' in r for r in manifest['runs']),
             'scenario_runs':sum('scenario' in r for r in manifest['runs']),
             'stock_parity_frames':sum(r.get('parity_frames',0) for r in manifest['runs']),
             'boot_parity_frames':sum(r.get('boot_parity_frames',0) for r in manifest['runs'])}
  (args.evidence/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
  print('PASS:', summary, 'NOT hardware/release clearance.')


if __name__ == '__main__':
  main()
