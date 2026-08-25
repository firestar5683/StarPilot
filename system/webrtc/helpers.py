import time
import requests
from dataclasses import asdict, dataclass, field


WEBRTCD_PORT = 5001


@dataclass
class StreamRequestBody:
  sdp: str
  init_camera: str = ""
  enabled: bool = True
  cameras: list[str] = field(default_factory=list)
  bridge_services_in: list[str] = field(default_factory=list)
  bridge_services_out: list[str] = field(default_factory=list)

  def __post_init__(self):
    if not self.cameras:
      if self.init_camera:
        self.cameras = [self.init_camera]
      else:
        self.cameras = ["road"]
    if not self.init_camera and self.cameras:
      self.init_camera = self.cameras[0]


def post_stream_request(body: StreamRequestBody) -> dict:
  t_start = time.monotonic()
  try:
    resp = requests.post(f"http://localhost:{WEBRTCD_PORT}/stream", json=asdict(body), timeout=10)
    t_end = time.monotonic()
    ret = resp.json()
    ret["time"] = (t_end - t_start) * 1000
    return ret
  except requests.ConnectTimeout as e:
    raise Exception("webrtc took too long to respond.") from e
  except requests.ConnectionError as e:
    raise Exception("webrtc server on device is not running.") from e


def wait_for_webrtcd(max_retries: float = 10) -> None:
  attempts = 0
  while attempts < max_retries:
    try:
      if requests.get(f"http://localhost:{WEBRTCD_PORT}/schema", timeout=1).ok:
        return
    except requests.ConnectionError:
      attempts += 1
      time.sleep(0.5)
  raise TimeoutError("webrtcd did not initialize in time.")
