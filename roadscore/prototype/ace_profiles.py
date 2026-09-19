"""Human-selected demo profiles; archived Circuit is intentionally not selectable."""
import os
PROFILES={'prism':{'name':'Prism','status':'primary'},'aurora':{'name':'Aurora','status':'backup'}}
def selected():
 value=os.environ.get('ROADSCORE_ACE_PROFILE','prism')
 if value not in PROFILES:raise ValueError('ACE profile must be prism or aurora')
 return value
