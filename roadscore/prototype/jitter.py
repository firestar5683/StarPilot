"""Bounded recovery on an authoritative sample clock; never shifts the timeline."""
def overdue_frames(target,dac,rate,available,tolerance=.02):
 lag=dac-target
 return min(available,max(0,round(lag*rate))) if lag>tolerance else 0
