import time
from opendbc.car.carlog import carlog
from opendbc.car.isotp_parallel_query import IsoTpParallelQuery

EXT_DIAG_REQUEST = b'\x10\x03'
EXT_DIAG_RESPONSE = b'\x50\x03'
RESET_REQUEST = b'\x11\x01'
RESET_RESPONSE = b''

def ecu_log(msg):
  carlog.warning(msg)


def disable_ecu(can_recv, can_send, bus=0, addr=0x7d0, sub_addr=None, com_cont_req=b'\x28\x83\x01', timeout=0.1, retry=10,
                reset=False, session_delay=0.05):
  """Silence an ECU by disabling sending and receiving messages using UDS 0x28.
  The ECU will stay silent as long as openpilot keeps sending Tester Present.

  This is used to disable the radar in some cars. Openpilot will emulate the radar.
  WARNING: THIS DISABLES AEB!"""
  ecu_log(f"=== ECU DISABLE START === addr={hex(addr)}, bus={bus}")

  if reset:
    try:
      ecu_log("sending ECU reset before communication control...")
      reset_query = IsoTpParallelQuery(can_send, can_recv, bus, [(addr, sub_addr)], [RESET_REQUEST], [RESET_RESPONSE])
      reset_query.get_data(timeout=timeout)
      time.sleep(0.2)
    except Exception as e:
      ecu_log(f"reset exception: {e}")

  # Try multiple times with different approaches
  for i in range(retry):
    try:
      # Enter extended diagnostic session
      ecu_log(f"attempt {i+1}/{retry}: diag session...")
      query = IsoTpParallelQuery(can_send, can_recv, bus, [(addr, sub_addr)], [EXT_DIAG_REQUEST], [EXT_DIAG_RESPONSE])

      for _, _ in query.get_data(timeout).items():
        ecu_log("diag session OK")

        # Some ECUs need a short settle time. The gated EV9 pre-fingerprint
        # probe uses zero delay to reach CommunicationControl before READY
        # conditions latch.
        if session_delay > 0:
          time.sleep(session_delay)

        # Send CC command and log the response
        ecu_log("sending CC...")
        cc_query = IsoTpParallelQuery(can_send, can_recv, bus, [(addr, sub_addr)], [com_cont_req], [b''])
        cc_response = cc_query.get_data(timeout)

        # Log what we got back
        cc_success = False
        cc_rejected = False
        cc_nrc = None
        for (_rx_addr, _), data in cc_response.items():
          ecu_log(f"CC response: {data.hex() if data else 'empty'}")
          # Check for positive response (0x68 = 0x28 + 0x40)
          if len(data) >= 1 and data[0] == 0x68:
            ecu_log("=== ECU DISABLE CONFIRMED ===")
            cc_success = True
          # Check for negative response
          elif len(data) >= 3 and data[0] == 0x7F:
            nrc = data[2]
            cc_nrc = nrc
            nrc_meanings = {
              0x12: "subFunctionNotSupported",
              0x13: "incorrectMessageLengthOrInvalidFormat",
              0x22: "conditionsNotCorrect (car must be in IGN-ON, not READY)",
              0x31: "requestOutOfRange",
              0x33: "securityAccessDenied",
            }
            nrc_name = nrc_meanings.get(nrc, "unknown")
            ecu_log(f"CC rejected: NRC 0x{nrc:02x} = {nrc_name}")
            cc_rejected = True

        if cc_success:
          return True
        elif cc_rejected:
          if reset and cc_nrc == 0x22 and i < retry - 1:
            ecu_log("CC rejected with NRC 0x22 after reset; retrying...")
            time.sleep(0.2)
            continue
          # ECU explicitly rejected - don't retry, it won't work
          ecu_log("=== ECU DISABLE REJECTED ===")
          return False
        elif len(com_cont_req) >= 2 and com_cont_req[1] & 0x80:
          # The UDS suppress-positive-response bit explicitly makes silence the
          # expected result. Preserve that behavior for legacy callers.
          ecu_log("=== ECU DISABLE SENT (positive response suppressed) ===")
          return True
        else:
          # An unsuppressed request (including EV9 28 01 01) transfers no
          # ownership without its 0x68 response. Retry, then fail closed.
          ecu_log("=== ECU DISABLE UNCONFIRMED (no response) ===")

    except Exception as e:
      ecu_log(f"attempt {i+1} exception: {e}")

    time.sleep(0.1)

  ecu_log("=== ECU DISABLE FAILED ===")
  return False
