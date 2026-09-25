"""Generic extended CAN FD wire endpoint, using the attributed shared codec."""
from opendbc.car.ford.mache_can import create_lat_ctl2_msg


def create_extended_canfd_msg(packer, CAN, active, ramp, precision, curvature, rate, counter):
  # Generic original lower rate negates to +.001024, outside the 11-bit field.
  # Clamp the physical wire endpoint before packing instead of wrapping sign.
  rate = max(-.001024, min(.001023, rate))
  return create_lat_ctl2_msg(packer, CAN, int(active), ramp, precision, curvature, rate, counter, 0.)
