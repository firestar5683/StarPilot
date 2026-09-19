"""Keep preparation status truthful when supervised processes fail."""
import json
import time


class LaunchFailure(RuntimeError):
  def __init__(self, component, code, connection=False):
    self.component, self.code, self.connection = component, code, connection
    super().__init__(f'{component} exited with status {code}; see {component}.log')


def check_children(children, *, remote, include_receiver=False, allow_clean_receiver=False):
  names = ['semantic_planner', 'semantic_tunnel'] + (['receiver'] if include_receiver else [])
  for name in names:
    child = children.get(name)
    if child is None:
      continue
    code = child.poll()
    if code is not None and not (name == 'receiver' and code == 0 and allow_clean_receiver):
      raise LaunchFailure(name, code, name == 'semantic_tunnel' or (name == 'receiver' and remote and code == 255))


def describe_failure(error):
  connection = isinstance(error, LaunchFailure) and error.connection
  return {'readiness': 'DEGRADED', 'job_inflight': False,
          'failure_kind': 'connection_lost' if connection else 'launch_failed',
          'failure_component': getattr(error, 'component', 'launcher'),
          'failure_exit_code': getattr(error, 'code', None),
          'failure_cause': str(error)[-2000:], 'failure_time': time.time()}


def write_failure(path, failure):
  try:
    state = json.loads(path.read_text())
  except (OSError, ValueError):
    state = {}
  state.update(failure)
  temporary = path.with_name(path.name + '.failure.tmp')
  temporary.write_text(json.dumps(state))
  temporary.replace(path)
