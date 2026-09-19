import json
from bundle import OLD,OUT
catalog=[]
for p in sorted((OLD/'profiles').iterdir()):
 if not (p/'profile.json').exists():continue
 meta=json.loads((p/'profile.json').read_text());audit_path=OUT/(p.name+'_native_profile_plan_audit.json');audit=json.loads(audit_path.read_text()) if audit_path.exists() else [];tested=len(audit)==len(meta['roles']) and all(x['finite'] and x.get('preserved_prefix_exact',True) for x in audit);catalog.append({'identity':p.name,'style':meta['style'],'template_bytes':sum(f.stat().st_size for f in p.rglob('*.npy')),'roles':list(meta['roles']),'native_standalone_durations':[30,45,60],'native_sequential_tested':p.name=='prism' or tested,'native_full_route_tested':p.name=='prism','human_approval':p.name in ('prism','aurora'),'demo_status':{'prism':'primary','aurora':'backup','circuit':'archive'}.get(p.name,'archive'),'active':p.name in ('prism','aurora'),'shared_weights':'../weights and ../vae_weights, no duplicated weights','new_identity_preparation':'Mac official text/reference/audio-code encoders','native_runtime':'DiT, Euler sampling and VAE on Chestnut; noise, endpoint checks and arrangement on CPU'})
(OUT/'identity_catalog.json').write_text(json.dumps(catalog,indent=2));print(catalog)
