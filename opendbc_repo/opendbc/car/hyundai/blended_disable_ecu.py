"""Experimental mixed longitudinal diagnostic protocol."""
import time
from opendbc.car.carlog import carlog
from opendbc.car.isotp_parallel_query import IsoTpParallelQuery

EXT_DIAG_REQUEST = b'\x10\x03'
EXT_DIAG_RESPONSE = b'\x50\x03'
RESET_REQUEST = b'\x11\x01'
RESET_RESPONSE = b''
ecu_log = carlog.warning


def disable_ecu(can_recv, can_send, bus=0, addr=0x7d0, sub_addr=None, com_cont_req=b'\x28\x83\x01', timeout=0.1, retry=10, reset=False,
                require_response=False, diag_request=EXT_DIAG_REQUEST, diag_response=EXT_DIAG_RESPONSE, response_offset=0x8):
  """Silence an ECU by disabling sending and receiving messages using UDS 0x28.
  The ECU will stay silent as long as openpilot keeps sending Tester Present.
  Set require_response for takeovers that must fail closed unless the ECU confirms communication control.

  This is used to disable the radar in some cars. Openpilot will emulate the radar.
  WARNING: THIS DISABLES AEB!"""
  ecu_log(f"=== ECU DISABLE START === addr={hex(addr)}, bus={bus}")

  if reset:
    try:
      ecu_log("sending ECU reset before communication control...")
      reset_query = IsoTpParallelQuery(can_send, can_recv, bus, [(addr, sub_addr)], [RESET_REQUEST], [RESET_RESPONSE],
                                       response_offset=response_offset)
      reset_query.get_data(timeout=timeout)
      time.sleep(0.2)
    except Exception as e:
      ecu_log(f"reset exception: {e}")

  # Try multiple times with different approaches
  for i in range(retry):
    try:
      # Enter extended diagnostic session
      ecu_log(f"attempt {i+1}/{retry}: diag session...")
      query = IsoTpParallelQuery(can_send, can_recv, bus, [(addr, sub_addr)], [diag_request], [diag_response],
                                 response_offset=response_offset)

      for _, _ in query.get_data(timeout).items():
        ecu_log("diag session OK")

        # Small delay to let ECU fully enter diagnostic mode
        time.sleep(0.05)

        # Send CC command and log the response
        ecu_log("sending CC...")
        cc_query = IsoTpParallelQuery(can_send, can_recv, bus, [(addr, sub_addr)], [com_cont_req], [b''],
                                      response_offset=response_offset)
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
        elif require_response:
          ecu_log("CC response required but none received; retrying...")
          continue
        else:
          # No response - consider it sent (ECU might have stopped responding)
          ecu_log("=== ECU DISABLE SENT (no response) ===")
          return True

    except Exception as e:
      ecu_log(f"attempt {i+1} exception: {e}")

    time.sleep(0.1)

  ecu_log("=== ECU DISABLE FAILED ===")
  return False




def communication_control(can_recv, can_send, *, bus, addr, control_type, reset=False, timeout=.1, retry=10):
  """Matched unsuppressed SID/subfunction acknowledgment, following UdsClient.

  Original suppressed28 83/80 are preserved above as source sent-request
  behavior, never reused as confirmed takeover/restoration proof.
  """
  if reset:
    try:
      query = IsoTpParallelQuery(can_send, can_recv, bus, [(addr, None)], [RESET_REQUEST], [RESET_RESPONSE])
      query.get_data(timeout)
      time.sleep(.2)
    except Exception:
      carlog.exception('Mixed-CAN pre-takeover reset query failed')
  for _ in range(retry):
    try:
      diagnostic = IsoTpParallelQuery(can_send, can_recv, bus, [(addr, None)],
                                     [EXT_DIAG_REQUEST], [EXT_DIAG_RESPONSE])
      if not diagnostic.get_data(timeout):
        continue
      control = IsoTpParallelQuery(can_send, can_recv, bus, [(addr, None)],
                                  [bytes((0x28, control_type, 1))], [bytes((0x68, control_type))])
      if control.get_data(timeout):
        return True
    except Exception:
      carlog.exception('Mixed-CAN communication-control acknowledgment failed')
  return False


def confirm_disable_ecu(can_recv, can_send, *, bus, addr, com_cont_req, reset):
  if com_cont_req != b'\x28\x03\x01' or reset is not True:
    raise ValueError('Unexpected mixed-CAN takeover request')
  return communication_control(can_recv, can_send, bus=bus, addr=addr, control_type=3, reset=True)


def restore_ecu(can_recv, can_send, *, bus, addr, timeout=.1, retry=10):
  return communication_control(can_recv, can_send, bus=bus, addr=addr, control_type=0, timeout=timeout, retry=retry)
