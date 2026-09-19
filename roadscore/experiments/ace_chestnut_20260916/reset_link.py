"""Bounded offroad recovery using the installed USB controller's documented power API."""
import time,fcntl,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'prototype'))
from native_ownership import verify_offroad
verify_offroad()
from tinygrad.runtime.support.usb import USB3,CustomASM24Controller
lock=open('/data/roadscore/generated/gpu.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
devices=USB3.list_devices(0x3801,0x0001);assert len(devices)==1
usb=USB3(devices[0][0]);usb.control_write(0xF3,value=0,timeout=10000);time.sleep(2);usb.control_write(0xF3,value=1,timeout=10000);time.sleep(2)
controller=CustomASM24Controller(usb);print('PCIE_LINK',hex(controller.read(0xB450,1)[0]),flush=True)
