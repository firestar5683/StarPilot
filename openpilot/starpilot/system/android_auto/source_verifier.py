"""Fail-closed daemon check of a Galaxy-minted pairing source over loopback."""
from __future__ import annotations

import http.client
import re

SOURCE_ID = re.compile(r'[0-9a-f]{64}\Z')


class GalaxySourceVerifier:
  def __init__(self, host: str = '127.0.0.1', port: int = 8082, timeout: float = 1.0):
    self.host, self.port, self.timeout = host, port, timeout

  def valid(self, source: str) -> bool:
    if not isinstance(source, str) or not SOURCE_ID.fullmatch(source):
      return False
    connection = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
    try:
      connection.request('GET', '/api/android-auto/source/' + source)
      response = connection.getresponse()
      response.read(512)
      return response.status == 200
    except (OSError, TimeoutError, http.client.HTTPException):
      return False
    finally:
      connection.close()
