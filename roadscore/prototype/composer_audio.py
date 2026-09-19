"""PCM append boundaries independent of model latent rates."""
def result_window(meta,total_frames,rate,legacy_end):
 if 'new_audio_start_frame' in meta:
  if meta.get('sample_rate')!=rate:raise ValueError('Composer PCM rate does not match its frame metadata')
  start=int(meta['new_audio_start_frame'])-int(meta['overlap_frames']);end=int(meta.get('audio_end_frame',total_frames))
  if not 0<=start<end<=total_frames:raise ValueError('Invalid composer PCM append boundaries')
  return start,end
 return max(0,round((meta['retained_seconds']-2)*rate)),legacy_end
