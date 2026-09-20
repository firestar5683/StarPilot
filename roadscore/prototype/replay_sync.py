"""Opt-in, muted Mac replay following using original model timestamps.

No network or process control lives here. The caller supplies a validated Galaxy
snapshot and fresh local replay state, then writes a bounded absolute seek only
to its own uniquely prefixed replay command file. Clock domains never mix.
"""
import math


def finite(value):
  return type(value) in (int, float) and math.isfinite(value)


def start_deadline(value, session, now):
  """Accept only this launch's short-lived local-monotonic start barrier."""
  if (not isinstance(value, dict) or set(value) != {'session_id', 'play', 'start_at_wall'}
      or value['session_id'] != session or value['play'] is not True):return None
  deadline = value['start_at_wall']
  if not finite(deadline) or not now-1 <= deadline <= now+5:return None
  return max(now, deadline)


def validate_follow_options(args):
  if not args.follow_playhead:return
  if not args.muted or not args.paired_comma or args.no_control_server:
    raise ValueError('--follow-playhead requires --muted, an explicit paired peer, and the local follower')
  args.port = 0
  args.no_browser = True


class ReplayFollower:
  def __init__(self, route, first_model_ns, *, duration=float('inf'), deadband=.25, max_seek=3., cooldown=3.):
    self.route, self.first_model_ns = route, first_model_ns
    self.deadband, self.max_seek, self.cooldown = deadband, max_seek, cooldown
    self.duration = duration
    self.session = None
    self.last_issue = float('-inf')
    self.pending = None
    self.last_peer_model = None
    self.peer_progress_wall = None

  def evaluate(self, snapshot, local_model_ns, local_received, replay, *, now, replay_age):
    result = dict(status='paused', reason='peer_unavailable', skew_seconds=None, command=None)
    def reject(reason):
      result['reason'] = reason
      return result
    if not isinstance(snapshot, dict):return result
    status = snapshot.get('peer_status')
    if not isinstance(status, dict):return reject('invalid_peer_playhead')
    peer = status.get('demo')
    if not isinstance(peer, dict):return reject('invalid_peer_playhead')
    playhead = peer.get('playhead', {})
    if not isinstance(playhead, dict):return reject('invalid_peer_playhead')
    session = snapshot.get('session_id')
    if (snapshot.get('route') != self.route or peer.get('route') != self.route):return reject('peer_route_mismatch')
    if not isinstance(session, str) or not session or peer.get('session_id') != session:return reject('invalid_peer_session')
    if self.session is not None and session != self.session:return reject('peer_session_changed')
    if peer.get('available') is not True or peer.get('readiness') != 'READY':return reject('peer_unready')
    names = ('source_model_ns', 'route_t', 'server_wall', 'sampled_wall')
    if not all(finite(playhead.get(name)) for name in names):return reject('invalid_peer_playhead')
    sent, received = snapshot.get('request_started_wall'), snapshot.get('received_wall')
    if not finite(sent) or not finite(received):return reject('invalid_peer_timing')
    rtt = received-sent
    server_age = playhead['server_wall']-playhead['sampled_wall']
    receipt_age = now-received
    if not 0 <= rtt <= .5 or not 0 <= server_age <= .75 or not 0 <= receipt_age <= 1.5:return reject('peer_stale')
    if playhead.get('paused', False) is not False or playhead.get('playback_speed', 1) != 1:return reject('peer_not_playing_1x')
    peer_ns = playhead['source_model_ns']
    if peer_ns <= 0 or abs((peer_ns-self.first_model_ns)/1e9-playhead['route_t']) > .1:return reject('peer_archive_clock_mismatch')
    self.session = session
    if peer_ns != self.last_peer_model:
      self.last_peer_model, self.peer_progress_wall = peer_ns, now
    elif now-self.peer_progress_wall > .75:return reject('peer_model_stopped')
    if (not finite(local_model_ns) or local_model_ns <= 0 or not finite(local_received)
        or not 0 <= now-local_received <= .6):return reject('local_model_stale')
    if (not isinstance(replay, dict) or not finite(replay_age) or not 0 <= replay_age <= .5
        or any(not finite(replay.get(name)) for name in ('cur_sec', 'min_sec', 'max_sec'))
        or replay.get('paused') is not False or replay.get('speed') != 1):return reject('local_replay_unready')
    # Each age is a duration measured entirely within one clock domain.
    peer_now = peer_ns/1e9 + server_age + rtt/2 + receipt_age
    local_now = local_model_ns/1e9 + now-local_received
    skew = peer_now-local_now
    result.update(skew_seconds=skew, rtt_seconds=rtt, peer_status_age_seconds=server_age,
                  peer_session_id=session, local_model_ns=local_model_ns, peer_model_ns=peer_ns)
    if abs(skew) > 15:return reject('skew_out_of_bounds')
    if abs(skew) <= self.deadband:
      result.update(status='tracking', reason=None)
      return result
    if now-self.last_issue < self.cooldown:return reject('correction_cooldown')
    if self.pending is not None and now <= self.pending['expires']:return reject('correction_pending')
    delta = max(-self.max_seek, min(self.max_seek, skew))
    source_target = (local_model_ns-self.first_model_ns)/1e9 + now-local_received + delta
    if not -.25 <= source_target <= self.duration:return reject('seek_outside_archive')
    # Transport seeks are absolute route seconds, unlike archive-relative route_t.
    current = replay['cur_sec']+replay_age
    target = current+delta
    if not replay['min_sec'] <= current <= replay['max_sec'] or not replay['min_sec'] <= target <= replay['max_sec']:
      return reject('seek_outside_route')
    result.update(status='correcting', reason=None, command={'seek':target}, correction_seconds=delta)
    return result

  def issued(self, result, now, anchor_drift):
    """Authorize one matching PCM reanchor only after the seek file was written."""
    self.last_issue = now
    self.pending = dict(expires=now+5., delta=result['correction_seconds'], anchor_drift=anchor_drift)

  def consume_reanchor(self, drift, now):
    pending = self.pending
    if pending is None or now > pending['expires']:return False
    change = drift-pending['anchor_drift']
    delta = pending['delta']
    if (abs(change) <= self.max_seek+.75 and abs(change) >= max(.1, abs(delta)*.5)
        and abs(change-delta) <= min(.4, abs(delta)*.5)):
      self.pending = None
      return True
    return False
