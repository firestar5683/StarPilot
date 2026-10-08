import errno
import os
import shutil
import stat
import tarfile
import tempfile
import time
from typing import BinaryIO

from openpilot.starpilot.galaxy.drive_history import DIR_FLAGS, FILES, _same_directory
from openpilot.starpilot.galaxy.recording_media import MAX_SOURCE_BYTES, MediaLease, VerifiedRecording, RecordingMediaChanged, RecordingMediaUnsupported

NAME_ATTR = 'user.galaxy.name'
PRESERVE_ATTR = 'user.preserve'


def display_name(value):
  if type(value) is not str or not value.strip() or len(value.encode()) > 128 or any(ord(c) < 32 for c in value):
    raise ValueError('Choose a name of 1–128 bytes')
  return value.strip()


def attribute(fd, key):
  getxattr = getattr(os, 'getxattr', None)
  if getxattr is None:
    return b''
  try:
    return getxattr(fd, key)
  except OSError as error:
    if error.errno in (errno.ENODATA, errno.ENOTSUP):
      return b''
    raise


def raw_lease(source):
  try:
    return MediaLease(source, os.dup(source.source_fd))
  except Exception:
    source.close()
    raise


class RecordingLibrary:
  def __init__(self, history):
    self.history = history

  def describe(self, result):
    for route in result['routes']:
      route['displayName'] = route['routeId']
      route['preserved'] = False
      for segment in route['segments']:
        root = fd = -1
        try:
          root = os.open(self.history.root, DIR_FLAGS)
          fd = os.open(segment['segmentName'], DIR_FLAGS, dir_fd=root)
          segment['logBytes'] = {}
          for filename in sorted(os.listdir(fd)):
            if filename in {'rlog.zst', 'rlog.bz2', 'qlog.zst', 'qlog.bz2'}:
              info = os.stat(filename, dir_fd=fd, follow_symlinks=False)
              if stat.S_ISREG(info.st_mode) and info.st_size > 0:
                segment['logBytes'][filename] = info.st_size
          segment['logFiles'] = list(segment['logBytes'])
          route['preserved'] |= attribute(fd, PRESERVE_ATTR) == b'1'
          name = attribute(fd, NAME_ATTR).decode('utf-8')
          if not name:
            with os.scandir(fd) as entries:
              name = next((entry.name for entry in entries if entry.is_file(follow_symlinks=False) and
                           entry.name not in FILES and not entry.name.endswith(('.lock', '.png', '.gif', '.json')) and
                           entry.stat(follow_symlinks=False).st_size == 0), '')
          if name:
            route['displayName'] = name
        except (OSError, UnicodeError):
          pass  # Optional labels never hide a recording.
        finally:
          if fd >= 0:
            os.close(fd)
          if root >= 0:
            os.close(root)
    return result

  def open_log(self, segment_name, filename):
    if filename not in {'rlog.zst', 'rlog.bz2', 'qlog.zst', 'qlog.bz2'}:
      raise ValueError('Invalid recording log')
    return raw_lease(VerifiedRecording(self.history.root, segment_name, filename))

  def open_archive(self, route_id, *, permitted):
    inventory = self.history.snapshot()
    route = next((route for route in inventory['routes'] if route['routeId'] == route_id), None)
    if inventory['scanIncomplete'] or route is None:
      raise ValueError('Complete route inventory unavailable')
    source = LogArchive()
    deadline = time.monotonic() + 30
    try:
      route = self.describe({'routes': [route]})['routes'][0]
      for segment in route['segments']:
        for filename in segment.get('logFiles', []):
          source.sources.append(VerifiedRecording(self.history.root, segment['segmentName'], filename))
      if not source.sources:
        raise ValueError('No saved logs for this drive')
      if sum(item.identity[2] for item in source.sources) > MAX_SOURCE_BYTES:
        raise RecordingMediaUnsupported('Logs are too large to archive; download individual files')
      with tempfile.TemporaryFile(prefix='galaxy-logs-') as output:
        with tarfile.open(fileobj=output, mode='w') as archive:
          for item in source.sources:
            info = tarfile.TarInfo(item.name + '/' + item.source_name)
            info.size = item.identity[2]
            info.mtime = item.identity[3] // 1_000_000_000
            with os.fdopen(os.dup(item.source_fd), 'rb') as opened:
              archive.addfile(info, CheckedLogReader(opened, item, permitted, deadline))
        if not permitted() or not source.current():
          raise RecordingMediaChanged
        return MediaLease(source, os.dup(output.fileno()))
    except Exception:
      source.close()
      raise

  def action(self, payload, *, permitted):
    if type(payload) is dict and payload.get('action') == 'delete-all':
      if set(payload) != {'action', 'confirmed', 'includePreserved'} or payload['confirmed'] is not True or \
         type(payload['includePreserved']) is not bool:
        raise ValueError('Confirm deletion first')
      if not permitted():
        raise PermissionError('Turn off the vehicle before managing recordings')
      inventory = self.history.snapshot()
      if inventory['scanIncomplete']:
        raise ValueError('Recording scan is incomplete; delete individual routes instead')
      deleted = 0
      for route in self.describe(inventory)['routes']:
        if payload['includePreserved'] or not route['preserved']:
          self.action({'action': 'delete', 'routeId': route['routeId'], 'confirmed': True}, permitted=permitted)
          deleted += 1
      return {'saved': True, 'deleted': deleted}
    if type(payload) is not dict or payload.get('action') not in {'rename', 'preserve', 'delete'}:
      raise ValueError('Invalid recording action')
    action = payload['action']
    fields = {'action', 'routeId'} | ({'name'} if action == 'rename' else {'preserved'} if action == 'preserve' else {'confirmed'})
    if set(payload) != fields or type(payload['routeId']) is not str:
      raise ValueError('Invalid recording action')
    if action == 'delete' and payload['confirmed'] is not True:
      raise ValueError('Confirm deletion first')
    if action == 'preserve' and type(payload['preserved']) is not bool:
      raise ValueError('Invalid preservation choice')
    name = display_name(payload['name']) if action == 'rename' else None
    if not permitted():
      raise PermissionError('Turn off the vehicle before managing recordings')
    # Use a complete scan so a route with an active or omitted segment cannot be partly deleted.
    inventory = self.history.snapshot()
    route = next((r for r in inventory['routes'] if r['routeId'] == payload['routeId']), None)
    if inventory['scanIncomplete'] or route is None:
      raise ValueError('Recording inventory changed; refresh before trying again')
    root = os.open(self.history.root, DIR_FLAGS)
    opened = []
    try:
      prefix = payload['routeId'].replace('|', '_') + '--'
      alternate = payload['routeId'] + '--'
      with os.scandir(root) as entries:
        names = [entry.name for entry in entries if entry.name.startswith((prefix, alternate))]
      if set(names) != {s['segmentName'] for s in route['segments']}:
        raise ValueError('This route still has an active segment')
      for segment in route['segments']:
        segment_name = segment['segmentName']
        fd = os.open(segment_name, DIR_FLAGS, dir_fd=root)
        opened.append((segment_name, fd))
        if not _same_directory(fd, root, segment_name) or any(n.endswith('.lock') for n in os.listdir(fd)):
          raise ValueError('Recording changed')
      if action == 'preserve' and payload['preserved']:
        preserved = self.describe(inventory)
        current = next(r for r in preserved['routes'] if r['routeId'] == payload['routeId'])
        if sum(r['preserved'] for r in preserved['routes']) >= 5 and not current['preserved']:
          raise ValueError('Maximum of 5 preserved routes reached')
      for segment_name, fd in opened:
        if (not permitted() or not _same_directory(root, None, self.history.root) or
            not _same_directory(fd, root, segment_name) or any(n.endswith('.lock') for n in os.listdir(fd))):
          raise PermissionError('Recording action is no longer available')
        if action == 'rename':
          os.setxattr(fd, NAME_ATTR, name.encode())
        elif action == 'preserve':
          if payload['preserved']:
            os.setxattr(fd, PRESERVE_ATTR, b'1')
          elif attribute(fd, PRESERVE_ATTR):
            os.removexattr(fd, PRESERVE_ATTR)
        else:
          shutil.rmtree(segment_name, dir_fd=root)
      return {'saved': True}
    finally:
      for _, fd in opened:
        os.close(fd)
      os.close(root)


class LogArchive:
  """Closed source leases remain verified throughout archive creation and serving."""
  def __init__(self):
    self.sources = []

  def current(self):
    return bool(self.sources) and all(source.current() for source in self.sources)

  def close(self):
    for source in self.sources:
      source.close()
    self.sources.clear()


class CheckedLogReader:
  def __init__(self, opened: BinaryIO, source, permitted, deadline):
    self.opened, self.source, self.permitted, self.deadline = opened, source, permitted, deadline

  def read(self, size: int = -1) -> bytes:
    if not self.permitted() or not self.source.current() or time.monotonic() > self.deadline:
      raise RecordingMediaChanged('Log archive preparation interrupted')
    return self.opened.read(size)
