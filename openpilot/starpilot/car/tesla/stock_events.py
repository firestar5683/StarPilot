import hashlib
import json

from openpilot.cereal import log
from opendbc.car.tesla.preap.aol import qualified


def cp_fingerprint(cp):
  if not qualified(cp):
    return None
  fields = (str(cp.carFingerprint), int(cp.flags), int(cp.alternativeExperience),
            tuple((str(c.safetyModel), int(c.safetyParam)) for c in cp.safetyConfigs),
            bool(cp.pcmCruise), bool(cp.openpilotLongitudinalControl), bool(cp.radarUnavailable))
  return hashlib.sha256(json.dumps(fields, separators=(',', ':')).encode()).hexdigest()


def publish_stock_status(pm, cp, internal, *, session, sequence, car_state_stamp, valid):
  from openpilot.cereal import messaging
  binding = cp_fingerprint(cp)
  if binding is None:
    return
  message = messaging.new_message('slcCruiseEvent', valid=valid)
  message.logMonoTime = car_state_stamp
  record = message.slcCruiseEvent
  record.kind = 'teslaStockCruise'
  record.eventId = sequence
  record.producerSessionId = session
  record.observedMonoTime = car_state_stamp
  record.teslaStockCruise = {'version': 1, 'carStateMonoTime': car_state_stamp, 'cpFingerprint': binding,
                            'engaged': internal.di_cruise_state == 'ENABLED',
                            'notArmed': internal.cruiseEnabled and internal.enableLongControl and
                                        internal.di_cruise_state not in ('STANDBY', 'ENABLED')}
  pm.send('slcCruiseEvent', message)


class StockCruiseConsumer:
  def __init__(self, cp):
    self.binding = cp_fingerprint(cp)
    self.session = None
    self.sequence = -1
    self.previous = False
    self.pending = []
    self.socket = None
    if self.binding is not None:
      from openpilot.cereal import messaging
      self.socket = messaging.sub_sock('slcCruiseEvent', conflate=False)

  def poll(self, events, sm, *, now_ns, session):
    from openpilot.cereal import messaging
    for _ in range(128):
      envelope = messaging.recv_one_or_none(self.socket)
      if envelope is None:
        break
      if envelope.which() == 'slcCruiseEvent' and str(envelope.slcCruiseEvent.kind) == 'teslaStockCruise':
        self.pending.append(envelope)
    self.pending = self.pending[-16:]
    current_stamp = sm.logMonoTime['carState']
    for envelope in self.pending:
      if envelope.logMonoTime == current_stamp:
        self.update(events, sm, envelope=envelope, now_ns=now_ns, session=session)
    self.pending = [item for item in self.pending if current_stamp < item.logMonoTime <= now_ns + 100_000_000]

  def update(self, events, sm, *, envelope, now_ns, session):
    try:
      record = envelope.slcCruiseEvent
      stock = record.teslaStockCruise
      cs = sm['carState']
      stamp = envelope.logMonoTime
      if (self.binding is None or not envelope.valid or not sm.valid['carState'] or not sm.alive['carState'] or
          not cs.canValid or cs.canTimeout or str(record.kind) != 'teslaStockCruise' or
          stock.version != 1 or stock.cpFingerprint != self.binding or not session or
          record.producerSessionId != session or
          not 0 < stock.carStateMonoTime == record.observedMonoTime == stamp == sm.logMonoTime['carState'] <= now_ns <= stamp + 100_000_000):
        return
      if self.session != session:
        self.session, self.sequence, self.previous = session, -1, False
      if record.eventId <= self.sequence:
        return
      self.sequence = record.eventId
      names = log.OnroadEvent.EventName
      if stock.engaged and not self.previous:
        events.add(names.teslaCCEngaged)
      elif not stock.engaged and self.previous:
        events.add(names.teslaCCDisengaged)
      if stock.notArmed:
        events.add(names.teslaCCNotArmed)
      self.previous = bool(stock.engaged)
    except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
      return
