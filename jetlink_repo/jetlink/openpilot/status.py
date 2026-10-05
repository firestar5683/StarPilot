"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

What the UI, hardwared and manager are told, in one snapshot, and the
progress the panels show while something provisions or joins.

Every answer here is files and params, no link IO: the UI asks five times a
second. The fork maps the snapshot onto its own widgets; the one mapping that
is jetlink's knowledge, which icon a state is, is Status.icon.

Light at module level: the package imports it, and the owner imports the package.
"""
from __future__ import annotations

import time
from typing import NamedTuple

from jetlink.comma import gadget

# -- progress -----------------------------------------------------------------
# Written by the provisioning run and the joining state, read by the UI: a
# param today (Keys.progress), because the writer is another process.

# Each report is a file write, and the UI reads it at 5 Hz. An upload reports
# once per 4 MB chunk, 440 of them for a 1.7 GB model, and onroad that is IO a
# recording would have to share the disk with.
PROGRESS_MIN_INTERVAL = 0.25


def estimated_build_seconds(size: int) -> int:
  """Orin Nano Super, TensorRT 10.3: the 766 MB models built in 102 to 166 s,
  the 1.75 GB ones in 230 to 294 s."""
  return int(60 + 130 * size / 1e9)


def _eta(seconds: float) -> str:
  if seconds >= 90:
    return f"about {seconds / 60:.0f} min left"
  return f"about {max(seconds, 1):.0f}s left"


class Progress:
  def __init__(self, op, size=None):
    self.op = op
    # () -> the picked model's size in bytes, or None: what the build's estimate is made from
    self._size = size
    self._last = ('', 0.0)

  def read(self) -> dict | None:
    """{stage, frac, msg} while something provisions, else None. Never raises."""
    try:
      value = self.op.get(self.op.keys.progress)
    except Exception:
      return None
    return value if isinstance(value, dict) else None

  def report(self, stage: str, frac: float, msg: str = '', drops: int = 0) -> None:
    """Never raises: called from except handlers. A fraction's ticks are held to
    4 Hz within a stage; a report with no fraction (a join's state) and the end
    of a stage always go through, so the panel's last word is never dropped. A
    join says 'waiting for jetlink' and 'checking the link keeps up' 50 ms apart;
    holding the second left the first on the panel for the rest of the drive.
    `msg` is the panel's one short line; `drops`, once the link has dropped often
    enough to blame the cable, is the panel's to word."""
    last_stage, last_at = self._last
    now = time.monotonic()
    if 0.0 < frac < 1.0 and stage == last_stage and now - last_at < PROGRESS_MIN_INTERVAL:
      return
    self._last = (stage, now)
    try:
      self.op.put(self.op.keys.progress, {'stage': stage, 'frac': round(frac, 4), 'msg': msg, 'drops': drops})
    except Exception:
      self.op.log.exception("jetlink: could not report progress")

  def clear(self) -> None:
    try:
      self.op.remove(self.op.keys.progress)
    except Exception:
      self.op.log.exception("jetlink: could not clear progress")

  def report_with_eta(self, stage: str, frac: float, msg: str = '') -> None:
    """Progress, with how long the build still has to run, from the model's
    size. Only the build: the upload reports MB of MB and a connect has nothing
    to predict."""
    if stage == 'build':
      size = self._size() if self._size is not None else None
      if size:
        msg = _eta(estimated_build_seconds(size) * max(0.0, 1.0 - frac))
    self.report(stage, frac, msg)


# -- what is on the other end -------------------------------------------------
# The owner (jetlink.comma.owner) writes all of this into its status record
# every step, presence and its hold included, so every reader agrees with it
# and with each other. Without a live record (no owner since boot, one that
# stopped cleanly, or one too old to write it) each reader reads the gadget's
# files itself, as below.

# the offroad alert for a link that is on while nobody holds the gadget: the
# owner's heartbeat stopped. manager starts it again, and its crash-loop
# backoff says so in its record's error while it waits
STOPPED = "service stopped"


def owner_record() -> tuple[dict | None, dict | None]:
  """The owner's status record, and the same record if it is live, else None.
  A stale record from an owner that was asked to stop is no record: manager
  SIGKILLed it in a slow teardown, and nothing is wrong."""
  record = gadget.owner_status()
  if record is None or gadget.owner_alive(record):
    return record, record
  return (None, None) if record.get('stopping') else (record, None)


class Presence:
  """Presence as a reader works it out from the files, for when the owner's
  record is not there to say."""

  def __init__(self):
    self._last_configured = 0.0

  def present(self) -> bool:
    """Is a host on the other end now: configured us, or did within
    PRESENCE_HOLD? A phone on the cable is a host on the gadget like any other."""
    if gadget.dormant():
      # no enumeration during suspend; the CC line still tells a sleeping host from an unplugged one
      return gadget.port_has_host()
    now = time.monotonic()
    if gadget.host_attached():
      self._last_configured = now
      return True
    return now - self._last_configured < gadget.PRESENCE_HOLD


def link_transport(mode: str | None = None, live: dict | None = None) -> str:
  """What carries the link, for the panels: a host on the vendor interface,
  or an iPhone dialed in over the network one. `live` is the owner's record;
  without it, `mode` stands in until the owner has said. Never raises."""
  try:
    if live is not None and live.get('link') in ('usb', 'cable'):
      kind, peer = live['link'], live.get('peer')
    else:
      kind, peer = gadget.link_state()
      kind = kind or gadget.link_kind(mode)
    if kind == 'cable' and not peer:
      # the owner records the phone while it holds the dial; a borrower that
      # took the dial itself noted it in the link record
      peer = gadget.link_state()[1]
    if kind == 'cable':
      return f"iOS over USB ({peer})" if peer else "iOS over USB"
  except Exception:
    pass
  return "USB"


def usb_port() -> str | None:
  """What the comma's USB-C port controller sees on the CC pin: 'empty', or
  'host' for a cable with something live behind it (it cannot say what). None
  where the kernel does not expose it, rather than claiming an empty port."""
  cc = gadget.cc_orientation()
  if cc is None:
    return None
  return 'host' if cc else 'empty'


# -- whether the link can run --------------------------------------------------

# the offroad alert's text for a device whose build made no warp for its camera
NO_WARP = "no warp built for this camera"


def unavailable(parts, record: dict | None) -> str | None:
  """Why an enabled link cannot run the large model, or None: files only.
  `record` is the owner's status record: its error when it is live, STOPPED
  when its heartbeat is not, and the gadget's own files without one."""
  if record is None:
    error = gadget.gadget_error()
  elif not gadget.owner_alive(record):
    return STOPPED
  else:
    error = record.get('error')
  if error:
    return str(error)
  return None if parts.warps.built() else NO_WARP


def _built_for_the_pick(parts) -> bool:
  spec = parts.spec.load()
  selected = parts.models.selected_model()
  return (spec is not None and selected is not None and spec.sha256 == selected['oid']
          and parts.spec.engine_ready_for(spec.sha256))


def reason(parts, mode: str) -> str | None:
  """Why the link cannot run, for someone who asked for it only: with it off,
  a device that cannot present the gadget simply does not offer the feature."""
  return unavailable(parts, owner_record()[0]) if parts.enabled(mode) else None


# -- the snapshot ----------------------------------------------------------------

class Status(NamedTuple):
  """Everything a reader shows, taken at once. Fields are only ever added."""
  enabled: bool                 # the setting is on and no chestnut is fitted
  mode: str                     # the Jetlink setting, one of MODES
  transport: str                # 'USB', or 'iOS over USB (<peer>)'
  present: bool                 # a host is on the gadget now, or asleep and known to be there
  port: str | None              # 'host' or 'empty' off the CC pin; None where the kernel does not say
  ready: bool                   # the picked model's engine is built (records only, no link IO)
  reason: str | None            # why an enabled link cannot run: the offroad alert's text
  progress: dict | None         # {stage, frac, msg} while provisioning or joining
  model: str | None             # the big model it will run: the pick, else jetlink's default
  default_model: str | None     # jetlink's default, named like the chestnut's (no build date)

  @property
  def active_model(self) -> str | None:
    """model, once it can run."""
    return self.model if self.ready else None

  def icon(self, started: bool, model_seen: bool, running_big: bool, state: str) -> str:
    """The chestnut icon's state for the link: a ChestnutState value.

    Offroad it is progress and the records; onroad, modelV2 and the joining
    model's state (modelDataV2SP.acceleratorState). `model_seen` is a modelV2
    since this drive started, `running_big` a live one that says big, and
    `state` the acceleratorState name.
    """
    if not started:
      stage = str((self.progress or {}).get('stage', ''))
      if not self.present:
        return 'disconnected'
      if stage and stage != 'ready':
        return 'failed' if stage == 'failed' else 'loading'
      return 'ready' if self.ready else 'uncompiled'

    if model_seen and running_big:
      return 'active'
    if not self.present:
      return 'disconnected'
    # attached, a pending join is loading, not a failed model
    if state in ('joining', 'retrying') or not model_seen:
      return 'loading'
    # the engine is up and only the swap window is missing: it opens when
    # nothing is in control, so a driver who stays engaged keeps the small model
    if state == 'ready':
      return 'waiting'
    if not self.ready:
      return 'uncompiled'
    if state == 'running':
      return 'active'
    return 'failed'


def read(parts, mode: str) -> Status:
  """Everything at once, over the link setting the caller read: each file once."""
  record, live = owner_record()
  enabled = parts.enabled(mode)
  reason = unavailable(parts, record) if enabled else None
  return Status(
    enabled=enabled,
    mode=mode,
    transport=link_transport(mode, live),
    present=bool(live.get('present')) if live is not None else parts.presence.present(),
    port=usb_port(),
    ready=enabled and reason is None and _built_for_the_pick(parts),
    reason=reason,
    progress=parts.progress.read(),
    model=parts.models.selected_model_name(),
    default_model=parts.models.default_model_name(),
  )


def failed(error: str, mode: str) -> Status:
  """What a reader gets when the snapshot itself failed: nothing to show, the
  setting as it is, and, for someone who asked for the link, the failure where
  the offroad alert puts it. A device with the link off is never nagged."""
  return Status(enabled=False, mode=mode, transport='USB', present=False, port=None, ready=False,
                reason=failure(error, mode), progress=None, model=None, default_model=None)


def failure(error: str, mode: str) -> str | None:
  return f"jetlink status failed: {error}" if mode != 'off' else None
