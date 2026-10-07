import hashlib
import json

from openpilot.cereal import log
from openpilot.selfdrive.selfdrived.events import Alert, ET, Priority, NormalPermanentAlert, VisualAlert
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

  def poll(self, sm, *, now_ns, session):
    from openpilot.cereal import messaging
    for _ in range(128):
      envelope = messaging.recv_one_or_none(self.socket)
      if envelope is None:
        break
      if envelope.which() == 'slcCruiseEvent' and str(envelope.slcCruiseEvent.kind) == 'teslaStockCruise':
        self.pending.append(envelope)
    self.pending = self.pending[-16:]
    current_stamp = sm.logMonoTime['carState']
    alerts = []
    for envelope in self.pending:
      if envelope.logMonoTime == current_stamp:
        alerts.extend(self.update(sm, envelope=envelope, now_ns=now_ns, session=session))
    self.pending = [item for item in self.pending if current_stamp < item.logMonoTime <= now_ns + 100_000_000]

    return alerts

  def update(self, sm, *, envelope, now_ns, session):
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
        return []
      if self.session != session:
        self.session, self.sequence, self.previous = session, -1, False
      if record.eventId <= self.sequence:
        return []
      self.sequence = record.eventId
      alerts = []
      if stock.engaged and not self.previous:
        alerts.append(stock_alert('engaged'))
      elif not stock.engaged and self.previous:
        alerts.append(stock_alert('disengaged'))
      if stock.notArmed:
        alerts.append(stock_alert('notArmed'))
      self.previous = bool(stock.engaged)
      return alerts
    except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
      return []


def stock_alert(kind):
  if kind == 'notArmed':
    alert = NormalPermanentAlert('Arm Stock Cruise to Enable Speed Control')
    alert.event_type = ET.PERMANENT
  else:
    engaged = kind == 'engaged'
    alert = Alert('Tesla Cruise Engaged' if engaged else 'Tesla Cruise Disengaged', '',
                  log.SelfdriveState.AlertStatus.normal, log.SelfdriveState.AlertSize.small,
                  Priority.LOW, VisualAlert.none,
                  log.SelfdriveState.AudibleAlert.engage if engaged else log.SelfdriveState.AudibleAlert.disengage, 0.8)
    alert.event_type = ET.WARNING
  alert.alert_type = f'teslaStockCruise/{kind}/{alert.event_type}'
  return alert
