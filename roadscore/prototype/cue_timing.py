"""Choose already-rendered musical cues at their scheduled audible time."""
import math

FIELDS = ('phase','kind','amount','activation','strength','section','next_section',
          'gesture_active','gesture_queued','turn_signal_music','lead','predicted_peak','scheduled',
          'signal_shaker','core_apex','alert_accent','engagement_presentation','motion_presentation')
REFERENCE = 'portaudio-dac-plus-residual-v1'


def audible_state(snapshot, now):
  if snapshot.get('presentation_timing_reference') != REFERENCE:
    return snapshot
  result = {key:value for key,value in snapshot.items() if key not in FIELDS}
  due = []
  for item in snapshot.get('presentation_timeline', []):
    if not isinstance(item,dict):continue
    wall=item.get('audible_wall')
    if type(wall) in (int,float) and math.isfinite(wall) and wall<=now and isinstance(item.get('cues'),dict):
      due.append(item)
  if due:
    selected=max(due,key=lambda entry:entry['audible_wall'])
    result.update({key:value for key,value in selected['cues'].items() if key in FIELDS})
    result['presentation_display_lateness_ms']=max(0,(now-selected['audible_wall'])*1000)
    result['presentation_display_sequence']=selected.get('sequence')
  return result
