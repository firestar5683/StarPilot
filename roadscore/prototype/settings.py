"""Product settings shared with future Galaxy controls. Session safety is separate."""
from dataclasses import dataclass,asdict
from audio_policy import session_muted
@dataclass(frozen=True)
class Settings:
 enabled: bool = True
 style: str = 'songform'
 mode: str = 'generate'
 muted: bool = False
 overlay: bool = True
 output_device: str | None = None
 profile: str = 'songform-experimental'
 def effective_muted(self,headless=False):
  return self.muted or headless or session_muted()
 def snapshot(self,headless=False):
  return {**asdict(self),'effective_muted':self.effective_muted(headless),'session_muted':session_muted()}
def resolve_route(parser,positional,legacy):
 if positional and legacy and positional != legacy:parser.error('Conflicting positional and --routeid values')
 route=positional or legacy
 if not route:parser.error('A route ID is required')
 return route
