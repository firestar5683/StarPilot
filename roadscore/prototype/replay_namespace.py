"""Choose Mac replay message ports without collisions between its services."""


def zmq_port(namespace, service):
  # Match the 64-bit FNV-1a mapping in msgq/impl_zmq.cc.
  value = 0xcbf29ce484222325
  endpoint = f'{namespace}:{service}' if namespace else service
  for byte in endpoint.encode():
    value = ((value ^ byte) * 0x100000001b3) & 0xffffffffffffffff
  return 8023 + value % (65535 - 8023)


def namespace_collisions(namespace, services):
  ports = {9000: ['camera']}
  for service in sorted(set(services)):
    ports.setdefault(zmq_port(namespace, service), []).append(service)
  return {port: names for port, names in ports.items() if len(names) > 1}


def choose_namespace(session, services, max_attempts=128):
  if max_attempts < 1:
    raise ValueError('At least one replay namespace attempt is required')
  services = tuple(services)
  if not services:
    raise ValueError('Replay services must be available before selecting message ports')
  base = 'roadscore-showcase-' + session
  for attempt in range(max_attempts):
    candidate = base if attempt == 0 else f'{base}-{attempt}'
    if not namespace_collisions(candidate, services):
      return candidate
  raise RuntimeError('Could not choose collision-free Mac replay message ports')
