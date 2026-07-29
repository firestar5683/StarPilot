import os
from cffi import FFI
from typing import Any, Protocol

from panda import LEN_TO_DLC

libpanda_dir = os.path.dirname(os.path.abspath(__file__))
libpanda_fn = os.path.join(libpanda_dir, "libpanda.so")

ffi = FFI()

ffi.cdef("""
typedef struct {
  unsigned char fd : 1;
  unsigned char bus : 3;
  unsigned char data_len_code : 4;
  unsigned char rejected : 1;
  unsigned char returned : 1;
  unsigned char extended : 1;
  unsigned int addr : 29;
  unsigned char checksum;
  unsigned char data[64];
} CANPacket_t;
""", packed=True)

ffi.cdef("""
typedef struct {
  uint8_t version;
  uint8_t state;
  uint8_t fingerprint;
  uint8_t attempts;
  uint8_t last_service;
  uint8_t last_response;
  uint8_t last_nrc;
  uint8_t communication_type;
  uint8_t trigger;
  uint8_t first_ecan_len;
  uint8_t powertrain_state;
  uint8_t powertrain_boot_state;
  uint8_t powertrain_init_state;
  uint8_t flags;
  uint16_t first_ecan_addr;
  uint32_t first_can_us;
  uint32_t state_started_us;
  uint32_t trigger_us;
  uint32_t first_ecan_us;
  uint32_t driver_braking_us;
  uint32_t pre_ready_us;
  uint32_t ignition_us;
  uint32_t session_response_us;
  uint32_t comm_control_us;
  uint32_t last_powertrain_us;
  uint32_t ready_us;
  uint32_t outcome_us;
} ev9_long_preinit_status_t;

typedef struct {
  uint8_t version;
  uint8_t page;
  uint8_t flags;
  uint8_t reserved;
  uint32_t cycle_started_us;
  uint32_t session_request_us;
  uint32_t session_response_us;
  uint32_t comm_control_us;
  uint32_t comm_control_response_us;
  uint32_t last_critical_adas_us;
  uint32_t first_replacement_us;
  uint32_t suppression_confirmed_us;
  uint32_t ready_us;
  uint32_t handoff_us;
  uint32_t restore_us;
  uint32_t abort_us;
  uint32_t last_host_tx_us;
  uint32_t last_tester_present_us;
  uint32_t last_vehicle_frame_us;
} ev9_long_preinit_timing_t;
""", packed=True)

ffi.cdef("""
int set_safety_hooks(uint16_t mode, uint16_t param);
void can_set_orientation(bool flipped);
""")

ffi.cdef("""
typedef struct {
  volatile uint32_t w_ptr;
  volatile uint32_t r_ptr;
  uint32_t fifo_size;
  CANPacket_t *elems;
} can_ring;

extern can_ring *rx_q;
extern can_ring *tx1_q;
extern can_ring *tx2_q;
extern can_ring *tx3_q;

bool can_pop(can_ring *q, CANPacket_t *elem);
bool can_push(can_ring *q, CANPacket_t *elem);
bool can_send_with_result(CANPacket_t *packet, uint8_t bus_number, bool skip_tx_hook);
bool can_send_ev9_preinit_with_result(CANPacket_t *packet, uint8_t bus_number);
void can_set_checksum(CANPacket_t *packet);
int comms_can_read(uint8_t *data, uint32_t max_len);
void comms_can_write(uint8_t *data, uint32_t len);
void comms_can_reset(void);
uint32_t can_slots_empty(can_ring *q);

void ev9_test_init(void);
void ev9_test_set_rx_idle(uint8_t bus_number, bool idle);
void ev9_test_set_reset_failed(bool failed);
void ev9_test_set_can_health(uint8_t bus_number, bool bus_off, bool error_passive,
                             uint8_t transmit_error_cnt);
uint32_t ev9_test_get_cancel_count(uint8_t bus_number);
uint32_t ev9_test_get_freeze_count(void);
void ev9_test_set_time(uint32_t now_us);
void ev9_test_rx(CANPacket_t *packet, uint32_t now_us);
void ev9_test_rx_isr_only(CANPacket_t *packet, uint32_t now_us);
void ev9_test_reset_cycle(void);
uint16_t ev9_test_current_safety_mode(void);
void ev9_test_tick(uint32_t now_us, bool ignition);
void ev9_test_tick_once(uint32_t now_us, bool ignition);
bool ev9_test_ignition_low_handoff_candidate(void);
bool ev9_test_warm_rearm_candidate(void);
void ev9_test_service_tx_cancel(uint32_t now_us);
void ev9_test_host_tx(CANPacket_t *packet, uint32_t now_us);
bool ev9_test_prepare_host_tx(CANPacket_t *packet, uint8_t bus_number, bool forwarded, uint32_t now_us);
void ev9_test_hw_tx(CANPacket_t *packet, uint32_t now_us);
bool ev9_test_request_release(uint16_t cycle_token, uint32_t now_us);
bool ev9_test_usb_request_allowed(uint8_t request, uint16_t param1, uint16_t param2);
bool ev9_test_must_preserve(void);
bool ev9_test_preserve_can_on_safety_transition(uint16_t mode, uint16_t param);
void ev9_test_host_watchdog_lost(uint32_t now_us, bool vehicle_live);
void ev9_test_tx_queue_cleared(uint8_t bus_number);
void ev9_test_set_heartbeat_counter(uint32_t counter);
bool ev9_test_external_tx_allowed(CANPacket_t *packet, uint8_t bus_number, bool forwarded);
bool ev9_test_tx_drain_allowed(uint8_t bus_number);
void ev9_test_update_crc(CANPacket_t *packet);
bool ev9_test_internal_bridge_allowed(CANPacket_t *packet);
uint8_t ev9_test_bus_from_can_num(uint8_t can_number);
uint8_t ev9_test_can_num_from_bus(uint8_t bus_number);
void ev9_test_get_status(ev9_long_preinit_status_t *status);
void ev9_test_get_timing(ev9_long_preinit_timing_t *timing);
""")

class CANPacket:
  reserved: int
  bus: int
  data_len_code: int
  rejected: int
  returned: int
  extended: int
  addr: int
  data: list[int]

class Panda(Protocol):
  # CAN
  tx1_q: Any
  tx2_q: Any
  tx3_q: Any
  def can_set_checksum(self, p: CANPacket) -> None: ...

  # safety
  def set_safety_hooks(self, mode: int, param: int) -> int: ...


libpanda: Panda = ffi.dlopen(libpanda_fn)


# helpers

def make_CANPacket(addr: int, bus: int, dat):
  ret = ffi.new('CANPacket_t *')
  ret[0].extended = 1 if addr >= 0x800 else 0
  ret[0].addr = addr
  ret[0].data_len_code = LEN_TO_DLC[len(dat)]
  ret[0].bus = bus
  ret[0].data = bytes(dat)
  libpanda.can_set_checksum(ret)

  return ret
