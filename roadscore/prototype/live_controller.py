"""Galaxy contract. Missing target health/lifecycle adapter is explicitly unavailable.

No SSH, device probing, or process start occurs while importing/constructing.
The target adapter must retain supervisor ownership across separate UI requests.
"""
from pathlib import Path
import time
from live_supervisor import blocked_reason


class LiveController:
    def __init__(self, root=Path('/data/roadscore'), *, adapter=None, clock=time.monotonic):
        self.root=Path(root);self.clock=clock;self.adapter=adapter
        if self.adapter is None:
            try:
                from live_target_adapter import create
            except ModuleNotFoundError as error:
                if error.name!='live_target_adapter':raise
            else:self.adapter=create(self.root)

    def status(self):
        if self.adapter is None:
            return dict(available=False,enabled=False,state='COLD',can_enable=False,
                        reason='Live target health/lifecycle adapter is not installed; hardware readiness is unverified')
        try:
            status=self.adapter.status()
            if status.get('available') is False:return status
            observation,authorization=self.adapter.health_and_authorization()
            reason=blocked_reason(observation,authorization,self.clock(),require_parked=True)
            return {**status,'available':True,'can_enable':not status.get('enabled',False) and not reason,
                    'reason':reason or status.get('reason','')}
        except Exception as error:
            return dict(available=False,enabled=None,state='DEGRADED',can_enable=False,reason='Live supervisor status unavailable: '+str(error))

    def set_enabled(self, enabled):
        if type(enabled) is not bool:raise ValueError('enabled must be a boolean')
        if self.adapter is None:
            if not enabled:return self.status()
            raise RuntimeError(self.status()['reason'])
        if not enabled:
            self.adapter.stop_owned()
            return self.status()
        observation,authorization=self.adapter.health_and_authorization()
        reason=blocked_reason(observation,authorization,self.clock(),require_parked=True)
        if reason:raise RuntimeError(reason)
        # Adapter must recheck atomically with launch and continue its watchdog.
        self.adapter.enable(observation,authorization)
        return self.status()


    def prepare_diagnostic(self):
        if self.adapter is None:raise RuntimeError('Live target adapter unavailable')
        return self.adapter.prepare_diagnostic()

    def confirm_driver_ready(self,session_id,*,audible=False):
        if self.adapter is None:raise RuntimeError('Live target adapter unavailable')
        return self.adapter.confirm_driver_ready(session_id,audible=audible)
