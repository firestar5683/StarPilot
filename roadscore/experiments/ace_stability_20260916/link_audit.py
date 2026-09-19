"""Read controller link/config after a failed process, before recovery. No power writes."""
import fcntl,json
from tinygrad.runtime.support.usb import USB3,CustomASM24Controller
lock=open('/data/roadscore/generated/gpu.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
devices=USB3.list_devices(0x3801,0x0001);assert len(devices)==1
usb=USB3(devices[0][0]);controller=CustomASM24Controller.__new__(CustomASM24Controller);controller.usb=usb
print('LINK_BEFORE_RECOVERY',hex(controller.read(0xB450,1)[0]),flush=True)
for offset in [0,4,0x10,0x14,0x18]:
 try:print('GPU_BUS4_CONFIG',hex(offset),hex(controller.pcie_cfg_req(offset,bus=4)),flush=True)
 except Exception as e:print('PCI_CONFIG_ERROR',hex(offset),str(e),flush=True);break
