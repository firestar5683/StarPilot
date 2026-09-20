"""Select a complete derived video cache without changing original route assets."""
import json
from pathlib import Path, PurePosixPath

SCHEMA='roadscore-playback-cache-v1'


def relative(value):
  if not isinstance(value,str) or '\\' in value:
    raise ValueError('Invalid cache path')
  path=PurePosixPath(value)
  if path.is_absolute() or '..' in path.parts or len(path.parts)!=2:
    raise ValueError('Invalid cache path')
  return path


def validated_playback(parent,route):
  parent=Path(parent);derived=parent/'playback'
  try:
    if (parent/'.acquiring').exists() or (derived/'.acquiring').exists():return None
    original=json.loads((parent/'cache_manifest.json').read_text())
    manifest=json.loads((derived/'playback_manifest.json').read_text())
    canonical=route.replace('|','/')
    if (manifest.get('schema')!=SCHEMA or manifest.get('route')!=canonical
        or original.get('route','').replace('|','/')!=canonical or manifest.get('complete') is not True):return None
    originals={entry['path']:entry for entry in original['files']}
    files=manifest['files']
    if not originals or len(files)!=len(originals) or len(originals)!=len(original['files']):return None
    if {entry['source'] for entry in files}!=set(originals) or len({entry['path'] for entry in files})!=len(files):return None
    name=canonical.split('/')[1]
    for entry in files:
      source=relative(entry['source']);target=relative(entry['path'])
      if source.parent!=target.parent or not source.parts[0].startswith(name+'--'):return None
      if not source.parts[0][len(name)+2:].isdigit():return None
      before=(parent/source).stat();after=(derived/target).stat()
      if not (parent/source).is_file() or not (derived/target).is_file():return None
      if before.st_size!=originals[str(source)]['bytes'] or before.st_size!=entry['source_bytes'] or before.st_mtime_ns!=entry['source_mtime_ns']:return None
      if after.st_size!=entry['bytes'] or after.st_size<=0:return None
      if source==target:
        if before.st_size!=after.st_size:return None
      else:
        if source.name!='fcamera.hevc' or target.name not in ('fcamera.h264','fcamera.ts'):return None
        if (derived/source).exists():return None
        video=entry['video_validation']
        if (type(video['source_frames']) is not int or video['source_frames']<=0
            or video['source_frames']!=video['output_frames']
            or type(video['width']) is not int or video['width']<=0
            or type(video['height']) is not int or video['height']<=0
            or video['frame_order_verified'] is not True or video['timing_verified'] is not True):return None
    return derived
  except (OSError,ValueError,KeyError,TypeError,IndexError):
    return None
