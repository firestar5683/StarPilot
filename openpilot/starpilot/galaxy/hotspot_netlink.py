"""Small nl80211 client for the one Galaxy AP interface; no wlan0 mutations."""
import socket
import struct


def attributes(data):
  result = {}
  while len(data) >= 4:
    size, kind = struct.unpack_from('HH', data)
    if size < 4 or size > len(data):
      raise ValueError('Malformed netlink attribute')
    result[kind & 0x3fff] = data[4:size]
    data = data[(size + 3) & ~3:]
  return result


def attribute(kind, data):
  size = len(data) + 4
  return struct.pack('HH', size, kind) + data + b'\0' * (-size % 4)


class WirelessInterfaces:
  def __init__(self):
    self.sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, 16)
    try:
      self.sock.settimeout(3)
      self.sock.bind((0, 0))
      self.sequence = 0
      self.family = int.from_bytes(self.query(16, 3, attribute(2, b'nl80211\0'))[0][1], 'little')
    except BaseException:
      self.sock.close()
      raise

  def close(self):
    self.sock.close()

  def query(self, family, command, payload=b'', *, dump=False, ack=False):
    self.sequence += 1
    message = struct.pack('BBH', command, 1, 0) + payload
    flags = 0x301 if dump else (5 if ack else 1)
    self.sock.sendto(struct.pack('IHHII', len(message) + 16, family, flags, self.sequence, 0) + message, (0, 0))
    replies = []
    while True:
      data = self.sock.recv(1024 * 1024)
      while len(data) >= 16:
        size, kind, _, seq, _ = struct.unpack_from('IHHII', data)
        if size < 16 or size > len(data):
          raise ValueError('Malformed netlink message')
        body, data = data[16:size], data[(size + 3) & ~3:]
        if seq != self.sequence:
          continue
        if kind == 3:
          return replies
        if kind == 2:
          error = struct.unpack_from('i', body)[0]
          if error:
            raise OSError(-error, 'Wi-Fi interface operation failed')
          if ack:
            return replies
          continue
        replies.append(attributes(body[4:]))
        if not dump and not ack:
          return replies

  def interfaces(self):
    return {row[4].rstrip(b'\0').decode(): {'index': int.from_bytes(row[3], 'little'),
            'phy': int.from_bytes(row[1], 'little'), 'type': int.from_bytes(row[5], 'little')}
            for row in self.query(self.family, 5, dump=True)}  # GET_INTERFACE

  def create(self, name, primary='wlan0'):
    interfaces = self.interfaces()
    if name in interfaces or interfaces[primary]['type'] != 2:  # station
      raise RuntimeError('Hotspot interface exists or primary Wi-Fi is not a client')
    payload = attribute(1, struct.pack('I', interfaces[primary]['phy']))
    payload += attribute(4, name.encode() + b'\0') + attribute(5, struct.pack('I', 3))  # AP
    self.query(self.family, 7, payload, ack=True)  # NEW_INTERFACE

  def delete(self, name):
    interfaces = self.interfaces()
    if name in interfaces:
      self.query(self.family, 8, attribute(3, struct.pack('I', interfaces[name]['index'])), ack=True)
