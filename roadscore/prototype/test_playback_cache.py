import json
from pathlib import Path
import tempfile
import unittest
from playback_cache import SCHEMA,validated_playback
from route_library import local_source

ROUTE='0123456789abcdef/2026-09-19--00-00-00'
NAME=ROUTE.split('/')[1]
class PlaybackCacheTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.parent=self.root/'routes'/ROUTE
  entries=[];derived=[]
  for segment in range(2):
   for name in ['rlog.zst','fcamera.hevc']:
    source=f'{NAME}--{segment}/{name}';p=self.parent/source;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'original')
    target=source.replace('.hevc','.h264');q=self.parent/'playback'/target;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b'original')
    entries.append(dict(path=source,bytes=8));row=dict(source=source,path=target,source_bytes=8,source_mtime_ns=p.stat().st_mtime_ns,bytes=8)
    if name.endswith('hevc'):row['video_validation']=dict(source_frames=1200,output_frames=1200,width=1928,height=1208,frame_order_verified=True,timing_verified=True)
    derived.append(row)
  (self.parent/'cache_manifest.json').write_text(json.dumps(dict(route=ROUTE,files=entries)))
  self.manifest=dict(schema=SCHEMA,route=ROUTE,complete=True,files=derived);self.save()
 def save(self):
  (self.parent/'playback/playback_manifest.json').write_text(json.dumps(self.manifest))
 def test_normal_path_selects_complete_derived_cache(self):
  self.assertEqual(local_source(ROUTE,self.root),self.parent/'playback')
 def test_stale_source_falls_back(self):
  (self.parent/self.manifest['files'][0]['source']).write_bytes(b'changed!')
  self.assertEqual(local_source(ROUTE,self.root),self.parent)
 def test_incomplete_wrong_route_and_acquiring_fall_back(self):
  for field,value in [('route','other'),('complete',False),('files',self.manifest['files'][:-1])]:
   before=self.manifest[field];self.manifest[field]=value;self.save();self.assertIsNone(validated_playback(self.parent,ROUTE));self.manifest[field]=before
  self.save();(self.parent/'playback/.acquiring').touch();self.assertEqual(local_source(ROUTE,self.root),self.parent)
 def test_video_count_order_and_missing_output_rejected(self):
  video=self.manifest['files'][1]['video_validation']
  for field,value in [('output_frames',1199),('frame_order_verified',False),('timing_verified',False)]:
   before=video[field];video[field]=value;self.save();self.assertIsNone(validated_playback(self.parent,ROUTE));video[field]=before
  self.save();(self.parent/'playback'/self.manifest['files'][1]['path']).unlink();self.assertIsNone(validated_playback(self.parent,ROUTE))
 def test_path_escape_and_duplicate_rejected(self):
  self.manifest['files'][0]['path']='../outside';self.save();self.assertIsNone(validated_playback(self.parent,ROUTE))

if __name__=='__main__':unittest.main()
