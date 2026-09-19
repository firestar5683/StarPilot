"""CPU-only offroad lease; never calls hardware power-save/amplifier APIs."""
def maintain(desired, offroad, read, write):
 if not offroad():return None
 changed=[]
 for path,value in desired.items():
  if read(path)!=value:
   # Stop before any further write if the real device transitions onroad.
   if not offroad():return None
   write(path,value);changed.append(path)
 return changed
