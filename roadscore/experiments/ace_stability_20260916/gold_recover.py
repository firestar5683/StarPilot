"""Recover original planner sequence; original random reference crops are unavailable."""
from prepare import *
gold=json.loads((R/'results/composition_20260916/ace/verse_to_chorus/benchmark.json').read_text())
codes=json.loads((OUT/'gold_planner_comparison.json').read_text())['original_codes']
run('gold_recovered_codes',gold['caption'],gold['lyrics'],40,12601,gold['reference_audio'],False,True,audio_codes=''.join('<|audio_code_'+str(c)+'|>' for c in codes))
p=OUT/'cases/gold_recovered_codes/case.json';m=json.loads(p.read_text());m['original_planner_codes_recovered']=True;m['original_reference_crop_state_recovered']=False;m['exact_original_reproduction']=False;p.write_text(json.dumps(m,indent=2))
