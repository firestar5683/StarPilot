"""Fail-closed live lifecycle policy. No Params writes, replay, or bench power code.

A target integration must supply genuine current observations and own the child
processes. Importing this module never probes a device or starts a process.
"""
from dataclasses import dataclass
import math
import time
import uuid


@dataclass(frozen=True)
class Observation:
    monotonic: float
    parked: bool
    model_fresh: bool
    car_fresh: bool
    modeld_healthy: bool
    device_healthy: bool
    chestnut_healthy: bool
    baseline_id: str
    car_id: str
    driving_model_local: bool = False


@dataclass(frozen=True)
class Authorization:
    baseline_id: str
    car_id: str
    coexistence_verified: bool = False
    user_authorized: bool = False


def blocked_reason(observation, authorization, now, *, require_parked):
    if not isinstance(observation, Observation) or not isinstance(authorization, Authorization):
        return 'Target health and explicit car/baseline authorization are unavailable'
    if authorization.user_authorized is not True or authorization.coexistence_verified is not True:
        return 'Car baseline and ACE/modeld coexistence must be verified and authorized'
    if not authorization.baseline_id or not authorization.car_id or (observation.baseline_id, observation.car_id) != (authorization.baseline_id, authorization.car_id):
        return 'Current car or software baseline differs from the authorized configuration'
    if not math.isfinite(observation.monotonic) or not 0 <= now-observation.monotonic <= 1.:
        return 'Live health observation is stale or has an invalid clock'
    if not all(value is True for value in (observation.model_fresh, observation.car_fresh, observation.modeld_healthy,
                observation.device_healthy, observation.chestnut_healthy, observation.driving_model_local)):
        return 'Fresh car/model input and healthy local driving model, device, and Chestnut are required'
    if require_parked and observation.parked is not True:
        return 'Park before preparing or enabling live RoadScore'
    return ''


class LiveSupervisor:
    """Adapter callbacks operate ONLY this session's worker/app, with no shell takeover.

    prepare(session_id) launches direct ACE with a fresh seed/current bank/quality.
    start_app(session_id) starts app --input live using accepted initial music.
    stop_owned() must terminate only this supervisor's owned process groups.
    These callbacks are deliberately injected, never an implicit hardware adapter.
    """
    def __init__(self, prepare, start_app, stop_owned, *, clock=time.monotonic):
        self.prepare=prepare;self.start_app=start_app;self.stop_owned=stop_owned;self.clock=clock
        self.state='COLD';self.reason='';self.session_id=None;self.enabled=False;self.driver_ready=False

    def status(self):
        return dict(available=True,enabled=self.enabled,state=self.state,reason=self.reason,
                    session_id=self.session_id,driver_ready=self.driver_ready)

    def enable(self, observation, authorization):
        if self.enabled:return self.status()
        reason=blocked_reason(observation,authorization,self.clock(),require_parked=True)
        if reason:raise RuntimeError(reason)
        self.session_id=uuid.uuid4().hex;self.driver_ready=False;self.enabled=True;self.state='PREPARING';self.reason='Preparing accepted audio while parked'
        try:self.prepare(self.session_id)
        except Exception:
            self.stop('Preparation failed');raise
        return self.status()

    def confirm_driver_ready(self, session_id, observation, authorization):
        if not self.enabled or self.state!='READY' or session_id!=self.session_id:
            raise RuntimeError('Driver readiness must confirm the current prepared live session')
        reason=blocked_reason(observation,authorization,self.clock(),require_parked=True)
        if reason:raise RuntimeError(reason)
        try:self.start_app(self.session_id)
        except Exception:
            self.stop('Live input/audio startup failed');raise
        self.driver_ready=True;self.state='STARTING';self.reason='Waiting for live input/audio readiness'
        return self.status()

    def tick(self, observation, authorization, *, worker_healthy, accepted_ready=False, app_ready=False, app_healthy=True):
        if not self.enabled:return self.status()
        reason=blocked_reason(observation,authorization,self.clock(),require_parked=not self.driver_ready)
        if reason or not worker_healthy or (self.driver_ready and not app_healthy):
            return self.stop(reason or 'Owned composer or audio process failed')
        if self.state=='PREPARING' and accepted_ready:
            self.state='READY';self.reason='Prepared while parked; explicit driver-ready confirmation required'
        if self.state=='STARTING' and app_ready:
            self.state='LIVE';self.reason=''
        return self.status()

    def stop(self, reason='Stopped by operator'):
        # Always callable, including when health is stale or car is moving.
        self.enabled=False;self.driver_ready=False;self.state='STOPPING';self.reason=reason
        try:self.stop_owned()
        except Exception:
            self.state='DEGRADED';self.reason='Owned process shutdown failed; inspect target supervisor';raise
        self.state='COLD';return self.status()
