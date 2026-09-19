"""Bounded LAN clock offset measurement; midpoint estimate with RTT/2 uncertainty."""
import json,subprocess,time

def measure(bench,samples=8):
 code='import sys,time,json\nfor line in sys.stdin:\n print(json.dumps({"remote":time.monotonic()}),flush=True)'
 p=subprocess.Popen(['ssh',bench,'/usr/local/venv/bin/python -u -c '+__import__('shlex').quote(code)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
 rows=[]
 try:
  for i in range(samples):
   before=time.monotonic();p.stdin.write('ping\n');p.stdin.flush();line=p.stdout.readline();after=time.monotonic()
   if not line:raise RuntimeError('Clock probe failed: '+p.stderr.read())
   remote=json.loads(line)['remote'];rows.append({'rtt_seconds':after-before,'bench_minus_host_seconds':remote-(before+after)/2,'uncertainty_seconds':(after-before)/2})
  best=min(rows,key=lambda x:x['rtt_seconds']);return {'method':'Eight request/reply samples over one SSH connection; smallest RTT midpoint. Assumes offset stable during run; uncertainty <=RTT/2 without symmetry assumption.','best':best,'samples':rows}
 finally:
  p.stdin.close();p.wait(timeout=10)
