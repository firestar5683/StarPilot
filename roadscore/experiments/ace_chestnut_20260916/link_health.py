"""Read-only link diagnostics through the current GPU owner. Never resets hardware."""
import json,time,os
from pathlib import Path
class LinkUnhealthy(RuntimeError):pass
class LinkProbe:
 def __init__(self,device,path):
  self.session=f'{os.getpid()}_{time.time_ns()}';self.dev=device;self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.last=None
 def sample(self,stage,**extra):
  dev=self.dev;row={'session':self.session,'owner_pid':os.getpid(),'stage':stage,'monotonic':time.monotonic(),'wall':time.time(),'timeline_target':getattr(dev,'timeline_value',0)-1,'architecture':getattr(dev,'arch',None),'vram_capacity_bytes':getattr(dev.iface.dev_impl,'vram_size',None),**extra}
  controller=dev.iface.pci_dev.usb
  for name,read in [('link_register',lambda:hex(controller.read(0xB450,1)[0])),('gpu_config',lambda:hex(controller.pcie_cfg_req(0,bus=4))),('bridge_config',lambda:hex(controller.pcie_cfg_req(0,bus=1))),('timeline_observed',lambda:int(dev.timeline_signal.value))]:
   try:row[name]=read()
   except Exception as e:row[name+'_error']=str(e)
  try:row['allocator_bytes']=sum(size for size,_,_,free in dev.iface.dev_impl.mm.pa_allocator.blocks.values() if not free)
  except Exception as e:row['allocator_error']=str(e)
  row['healthy']=row.get('link_register')=='0x78' and int(row.get('gpu_config','0'),16)&0xffff==0x1002
  with self.path.open('a') as f:f.write(json.dumps(row)+'\n')
  self.last=row;return row
 def preflight(self,**extra):
  row=self.sample('before_generation_job',**extra)
  if not row['healthy']:raise LinkUnhealthy('Chestnut link preflight failed; no generation submitted; explicit offroad recovery required')
  return row
 def install_failure_hook(self,contain=False):
  original=self.dev.on_device_hang
  def before_driver_handler():
   self.sample('before_driver_timeout_handler')
   if contain:raise LinkUnhealthy('GPU timeout captured; driver interrupt-reset handler skipped; explicit offroad recovery required')
   try:return original()
   finally:self.sample('after_driver_timeout_handler')
  self.dev.on_device_hang=before_driver_handler
 def trace(self,stage,start,n,timeline):self.sample(stage,latent_start=start,latent_count=n,submission_timeline=timeline)
