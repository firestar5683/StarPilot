"""Full normal replay regression and private archive retrieval. Runtime remains causal."""
import os,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'experiments/ace_stability_20260916'))
import bundle
bundle.OUT=R/'results/ace_demo_20260916'
# Reuse the established native-EOF/UI/causal audit, scoped to this pass's output.
source=(R/'experiments/ace_stability_20260916/replay_regressions.py').read_text()
source=source.replace("--composer ace --muted", "--composer ace --profile "+os.environ.get('ACE_PROFILE','prism')+" --muted")
if os.environ.get('ACE_PROFILE')=='aurora':
 source=source.replace("log=OUT/(label+", "label='aurora_'+label;log=OUT/(label+")
source=source.replace("if link.is_symlink():link.unlink();link.symlink_to(archive/'score.flac')","if link.is_symlink():link.unlink();link.symlink_to(archive/'score.flac')\n   quality_link=dest/'quality'\n   if quality_link.is_symlink():quality_link.unlink();quality_link.symlink_to(archive/'quality',target_is_directory=True)")
source=source.replace("full_route_pass=a['full_route_pass'])","full_route_pass=a['full_route_pass'],accepted_music_holds=len(a['safe_extensions']),quality_rejections=a['quality_rejections'],rerolls=a['rerolls'],accepted_jobs=a['accepted_jobs'])")
source=source.replace("rows=[r for r in rows if r['label']!=label]+[row]","row['summary']=row.get('summary','Launch did not reach an archive.')+f\" {len(a['safe_extensions']) if paths else 0} accepted-music holds.\";rows=[r for r in rows if r['label']!=label]+[row]")
exec(compile(source,str(Path(__file__)), 'exec'))
