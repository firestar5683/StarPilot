#pragma once

#include "opendbc/safety/declarations.h"

// safetyParam: 0 = CMA (XC40 Recharge), 1 = SPA (S60 Recharge, Polestar 2),
// 2 = C1 (V40)
// Polestar 2 is technically CMA, but appears to use SPA DBC for CAN 1 bus
#define VOLVO_FLAG_SPA 1U
#define VOLVO_FLAG_C1 2U

// Volvo CAN message addresses shared between CMA and SPA
#define VOLVO_LCA_STEER           0x58U    // TX from VCU1 to PSCM, LCA steering command (0x58)
#define VOLVO_LCA_2               0x69U   // RX from BCM, brake pedal, cruise state
#define VOLVO_SAS                 0x55U    // RX from SAS, steering angle sensor
#define VOLVO_PSCM                0x16U    // RX from PSCM, driver steering input
#define VOLVO_GEAR_POSITION       0x80U   // RX from transmission, gear position
#define VOLVO_DRIVER_INPUT        0x15U
#define VOLVO_LCA_3               0x57U   // TX from VCU1 to PSCM
#define VOLVO_LCA_5               0x67U   // TX LCA_5 message (formerly SPEED_1, contains wheel speeds and LCA signals)
#define VOLVO_SPEED               0x60U   // RX/TX SPEED message
#define VOLVO_SPEED_2             0x68U   // RX
#define VOLVO_0x1a                0x1aU   // RX
#define VOLVO_EGSM                0x45U   // RX from EGSM
#define VOLVO_PSCM_RELATED        0x17U   // RX from PSCM, related messages
#define VOLVO_LCA_4               0x90U   // TX LCA_4 message (PA status spoofing)
#define VOLVO_LCA_6               0x97U   // TX LCA_6 message
#define VOLVO_LCA_7               0x92U   // TX LCA_7 message

// C1-specific addresses (V40). The V40 powertrain bus is bus 0 and its
// forward-camera bus is bus 2; bus 1 is unused by this port.
#define VOLVO_C1_BUTTONS           0x10U
#define VOLVO_C1_FSM_0             0x30U
#define VOLVO_C1_FSM_1             0xD0U
#define VOLVO_C1_PSCM_1            0x125U
#define VOLVO_C1_PEDAL_AND_BRAKE   0x55U
#define VOLVO_C1_SPEED             0x150U

// CMA-specific PT bus addresses
#define VOLVO_CMA_BUS1_SPEED          0x70U   // RX vehicle speed
#define VOLVO_CMA_ECM_1               0x250U  // RX accelerator pedal position
#define VOLVO_CMA_BUS1_CRUISE_CONTROL 0x340U  // RX cruise control state

// SPA-specific PT bus addresses
#define VOLVO_SPA_BUS1_SPEED          0x75U   // RX vehicle speed
#define VOLVO_SPA_ECM_1               0x25U   // RX accelerator pedal position
#define VOLVO_SPA_BUS1_CRUISE_CONTROL 0x349U  // RX cruise control state

// SPEED (0x60) is raw counts in the DBC. Measured against GPS ground speed on two
// harnesses: implied LSB 0.0039736 and 0.0039792 m/s.
#define VOLVO_SPEED_TO_MS 0.003977f

// LCA_5_STEER is a signed 15-bit steering-wheel-angle command in 0.05596 deg/count.
// Keep the absolute envelope aligned with the software controller's 540 deg limit.
#define VOLVO_ANGLE_DEG_TO_CAN 17.869907f
#define VOLVO_MAX_ANGLE_CAN 9650
#define VOLVO_RELAY_ANGLE_TOLERANCE 54  // approximately 3 degrees

#define VOLVO_C1_ANGLE_DEG_TO_CAN 22.753128f
#define VOLVO_C1_MAX_ANGLE_CAN 8189
#define VOLVO_C1_RELAY_ANGLE_TOLERANCE 2


// CAN bus definitions for Volvo
// Using same naming as carstate.py for consistency: main, pt, party
#define VOLVO_MAIN_BUS    0U  // Bus.main - VCU1 car side
#define VOLVO_PT_BUS      1U  // Bus.pt - VCU1 ECM side (where ECM is)
#define VOLVO_PARTY_BUS   2U  // Bus.party - VCU PSCM/BCM2 side (BCM2, SAS, EGSM, PSCM, where LCA is sent to)

// Runtime addresses set by volvo_init based on safetyParam
static uint16_t volvo_ecm_1_addr;
static uint16_t volvo_bus1_cruise_control_addr;
static bool volvo_c1;

static int volvo_be_15(const CANPacket_t *msg, uint8_t byte) {
  return (int)(((uint16_t)(msg->data[byte] & 0x7FU) << 8U) | msg->data[byte + 1U]);
}

static int volvo_pscm_angle(const CANPacket_t *msg) {
  return to_signed(volvo_be_15(msg, 0U), 15);
}

static int volvo_lca_5_angle(const CANPacket_t *msg) {
  return to_signed(volvo_be_15(msg, 6U), 15);
}

static int volvo_c1_pscm_angle(const CANPacket_t *msg) {
  return (int)(((uint16_t)msg->data[5] << 8U) | msg->data[6]) - 32768;
}

static int volvo_c1_fsm_angle(const CANPacket_t *msg) {
  return (int)(((uint16_t)(msg->data[4] & 0x3FU) << 8U) | msg->data[5]) - 8192;
}

static uint8_t volvo_c1_fsm_checksum(const CANPacket_t *msg) {
  const uint16_t angle_raw = ((uint16_t)(msg->data[4] & 0x3FU) << 8U) | msg->data[5];
  const uint8_t direction = msg->data[7] & 0x3U;
  const uint8_t checksum_sum = (msg->data[3] + direction + angle_raw + (angle_raw >> 8U)) & 0xFFU;
  return checksum_sum ^ 0xFFU;
}

static const AngleSteeringLimits VOLVO_ANGLE_STEERING_LIMITS = {
  .max_angle = VOLVO_MAX_ANGLE_CAN,
  .angle_deg_to_can = VOLVO_ANGLE_DEG_TO_CAN,
  .angle_rate_up_lookup = {
    {0.0f, 5.0f, 25.0f},
    {5.0f, 3.0f, 0.4f},
  },
  .angle_rate_down_lookup = {
    {0.0f, 5.0f, 25.0f},
    {10.0f, 4.0f, 0.6f},
  },
  .frequency = 50U,
};

static const AngleSteeringLimits VOLVO_C1_ANGLE_STEERING_LIMITS = {
  .max_angle = VOLVO_C1_MAX_ANGLE_CAN,
  .angle_deg_to_can = VOLVO_C1_ANGLE_DEG_TO_CAN,
  .angle_rate_up_lookup = {
    {7.0f, 17.0f, 36.0f},
    {2.0f, 0.25f, 0.1f},
  },
  .angle_rate_down_lookup = {
    {7.0f, 17.0f, 36.0f},
    {2.0f, 0.25f, 0.1f},
  },
  .max_angle_error = 455,  // 20 degrees
  .angle_error_min_speed = 0.0f,
  .frequency = 50U,
  .enforce_angle_error = true,
};

static void volvo_rx_hook(const CANPacket_t *msg) {

  if (volvo_c1) {
    if (msg->bus == VOLVO_MAIN_BUS) {
      if (msg->addr == VOLVO_C1_PSCM_1) {
        update_sample(&angle_meas, volvo_c1_pscm_angle(msg));
      }

      if (msg->addr == VOLVO_C1_SPEED) {
        const uint16_t speed_raw = ((uint16_t)msg->data[6] << 8U) | msg->data[7];
        const float speed = ((float)speed_raw * 0.01f) / 3.6f;
        vehicle_moving = speed > 0.1f;
        UPDATE_VEHICLE_SPEED(speed);
      }

      if (msg->addr == VOLVO_C1_PEDAL_AND_BRAKE) {
        const uint16_t gas_raw = ((uint16_t)(msg->data[1] & 0x3U) << 8U) | msg->data[2];
        gas_pressed = gas_raw > 50U;  // DBC factor 0.1: greater than 5 percent
        brake_pressed = GET_BIT(msg, 24U) || GET_BIT(msg, 38U);
      }
    }

    if ((msg->bus == VOLVO_PARTY_BUS) && (msg->addr == VOLVO_C1_FSM_0)) {
      pcm_cruise_check(GET_BIT(msg, 58U));
    }
    return;
  }

  // Main bus (bus 0) messages
  if (msg->bus == VOLVO_MAIN_BUS) {
    // Update brake pedal and cruise state from BCM2
    if (msg->addr == VOLVO_LCA_2) {
      // DBC: SG_ BRAKE_PEDAL_PRESSED_A : 47|1@0+ (-1,1) - inverted in DBC, so we invert raw bit
      // DBC: SG_ BRAKE_PEDAL_PRESSED_B : 46|1@0+ (1,0) - not inverted
      //bool brake_a = !((msg->data[5] >> 7) & 1U); // Raw bit, active low (DBC inverts it)
      bool brake_b = (msg->data[5] >> 6) & 1U; // Raw bit, active high
      //brake_pressed = brake_a || brake_b;
      brake_pressed = brake_b;
    }

    // Vehicle speed from the main bus, matching carstate.py. The PT bus carries a
    // speed message too, but which car bus lands on PT is harness-dependent and its
    // scaling differs per PT DBC, so both sides read the main bus instead.
    // DBC: SG_ SPEED : 6|15@0+ (1,0) - raw counts, scaled here
    if (msg->addr == VOLVO_SPEED) {
      uint16_t speed_raw = ((msg->data[0] & 0x7FU) << 8) | msg->data[1];
      float speed = (float)speed_raw * VOLVO_SPEED_TO_MS;
      vehicle_moving = speed > 0.1;
      UPDATE_VEHICLE_SPEED(speed);
    }
  }

  // PT bus (bus 1) messages
  if (msg->bus == VOLVO_PT_BUS) {
    if (msg->addr == volvo_ecm_1_addr) {
      if (volvo_ecm_1_addr == VOLVO_CMA_ECM_1) {
        // CMA: SG_ ACCELERATOR_PEDAL_POS : 31|8@0+ (1,0) [0|255]
        uint8_t gas_pedal_position = msg->data[3];
        gas_pressed = gas_pedal_position > 21U; // 20 baseline + 1 tolerance
      } else {
        // SPA: SG_ ACCELERATOR_PEDAL_POS : 6|15@0+ (0.00390625,0) [0|32767] "%"
        uint16_t gas_raw = ((msg->data[0] & 0x7FU) << 8) | msg->data[1];
        gas_pressed = (gas_raw * 0.00390625) > 1.0; // > 1%
      }
    }

    if (msg->addr == volvo_bus1_cruise_control_addr) {
      bool cruise_enabled;
      if (volvo_bus1_cruise_control_addr == VOLVO_CMA_BUS1_CRUISE_CONTROL) {
        // CMA: SG_ CRUISE_CONTROL_ENABLED : 56|1@0+ and CRUISE_CONTROL_ENABLED_IDLE_TRAFFIC : 57|1@0+
        cruise_enabled = ((msg->data[7] & 1U) || (msg->data[7] & 2U));
      } else {
        // SPA: SG_ CRUISE_CONTROL_SPA_ENABLED : 1|1@0+ (-1,1) — byte 0 bit 1, active low
        cruise_enabled = !((msg->data[0] >> 1) & 1U);
      }
      pcm_cruise_check(cruise_enabled);
    }
  }

  // Party bus (bus 2) messages - BCM2, SAS, PSCM, EGSM
  if (msg->bus == VOLVO_PARTY_BUS) {

    if (msg->addr == VOLVO_PSCM) {
      // PSCM_ANGLE_SENSOR is the measurement consumed by carstate.py. It uses
      // the same signed 0.05596 deg/count representation as LCA_5_STEER.
      update_sample(&angle_meas, volvo_pscm_angle(msg));
    }

    // DRIVER_INPUT is the signal consumed by carstate.py for driver torque.
    // The PSCM frame's DRIVER_INPUT_DEVIATION is a different signal and must
    if (msg->addr == VOLVO_DRIVER_INPUT) {
      // STEERING_DRIVER_INPUT is a Motorola signal starting at bit 55. The
      // DBC also carries a +1 offset, so its raw byte is data[6].
      const int driver_input = to_signed(msg->data[6], 8) + 1;
      update_sample(&torque_driver, driver_input);
    }

  }
}

static bool volvo_tx_hook(const CANPacket_t *msg) {
  bool tx = true;

  if (volvo_c1) {
    if (msg->addr == VOLVO_C1_FSM_1) {
      const int desired_angle = volvo_c1_fsm_angle(msg);
      const uint8_t direction = msg->data[7] & 0x3U;
      const bool steer_control_enabled = direction != 0U;
      tx &= SAFETY_ABS(desired_angle) <= VOLVO_C1_MAX_ANGLE_CAN;
      tx &= !steer_angle_cmd_checks(desired_angle, steer_control_enabled, VOLVO_C1_ANGLE_STEERING_LIMITS);
      tx &= (direction == 0U) || (direction == 3U);
      tx &= (msg->data[0] == 0xE3U) && (msg->data[1] == 0xB4U) && (msg->data[2] == 0x08U);
      tx &= (msg->data[3] == 0x80U) && ((msg->data[4] & 0xC0U) == 0x80U) && ((msg->data[7] & 0xFCU) == 0x94U);
      tx &= msg->data[6] == volvo_c1_fsm_checksum(msg);
    }

    if (msg->addr == VOLVO_C1_PSCM_1) {
      const int relayed_angle = volvo_c1_pscm_angle(msg);
      const int measured_max = angle_meas.max + VOLVO_C1_RELAY_ANGLE_TOLERANCE;
      const int measured_min = angle_meas.min - VOLVO_C1_RELAY_ANGLE_TOLERANCE;
      tx &= !safety_max_limit_check(relayed_angle, measured_max, measured_min);
    }

    // Only ACC cancel (byte 7 bit 4) may be synthesized.
    if (msg->addr == VOLVO_C1_BUTTONS) {
      tx &= ((msg->data[7] & 0xEFU) == 0U) && (msg->data[6] == 0U);
    }
    return tx;
  }

  // LCA_5 carries the actual angle command used by the controller. The stock
  // LCA frame also contains an angle-shaped field, but the imported controller
  // deliberately leaves that field at the observed vehicle value.
  if (msg->addr == VOLVO_LCA_5) {
    const int desired_angle = volvo_lca_5_angle(msg);
    tx &= SAFETY_ABS(desired_angle) <= VOLVO_MAX_ANGLE_CAN;
    tx &= !steer_angle_cmd_checks(desired_angle, controls_allowed, VOLVO_ANGLE_STEERING_LIMITS);
  }

  // Keep the two torque-authority arms and the companion LCA angle bounded even
  // though these fields are not the primary steering command.
  if (msg->addr == VOLVO_LCA_STEER) {
    const int authority_pos = to_signed((int)(((uint16_t)(msg->data[0] & 0x07U) << 8U) | msg->data[1]), 11);
    const int authority_neg = to_signed((int)(((uint16_t)(msg->data[2] & 0x07U) << 8U) | msg->data[3]), 11);
    const int lca_angle = to_signed((int)(((uint16_t)(msg->data[5] & 0x3FU) << 8U) | msg->data[6]), 14);
    tx &= authority_pos >= 0 && authority_pos <= 614;
    tx &= authority_neg >= -614 && authority_neg <= 0;
    tx &= SAFETY_ABS(lca_angle) <= VOLVO_MAX_ANGLE_CAN;
  }

  // PSCM is relayed back onto the main bus to preserve the stock hands-on-wheel
  // path. Do not allow that relay to invent a steering-angle measurement.
  if (msg->addr == VOLVO_PSCM) {
    const int relayed_angle = volvo_pscm_angle(msg);
    const int measured_max = SAFETY_CLAMP(angle_meas.max + VOLVO_RELAY_ANGLE_TOLERANCE,
                                          -VOLVO_MAX_ANGLE_CAN, VOLVO_MAX_ANGLE_CAN);
    const int measured_min = SAFETY_CLAMP(angle_meas.min - VOLVO_RELAY_ANGLE_TOLERANCE,
                                          -VOLVO_MAX_ANGLE_CAN, VOLVO_MAX_ANGLE_CAN);
    tx &= !safety_max_limit_check(relayed_angle, measured_max, measured_min);
  }

  // NOTE: the wrong-bus rejections below are unreachable defense-in-depth:
  // safety_tx_hook() only calls this hook after the message passes the
  // VOLVO_TX_MSGS allowlist, which already pins each TX address to a single
  // bus (and VOLVO_DRIVER_INPUT/VOLVO_SAS are not TX'able on any bus).
  // Hence the GCOV_EXCL markers, following the defaults.h convention.
  // test_volvo.py's test_tx_hook_wrong_bus_blocked pins down the blocked
  // wrong-bus TX behavior at the safety_tx_hook() level.
  if (msg->addr == VOLVO_LCA_STEER) {
    // LCA message flows: VCU1 (main bus) -> PSCM (party bus)
    // We're acting as VCU1, so we send LCA message to party bus (bus 2)
    // GCOV_EXCL_START
    // Unreachable by design (allowlist pins VOLVO_LCA_STEER to the party bus)
    if (msg->bus != VOLVO_PARTY_BUS) {
      tx = false;  // Wrong bus
    }
    // GCOV_EXCL_STOP
  }

  if (msg->addr == VOLVO_PSCM) {
    // PSCM message: we relay from party bus (bus 2) to main bus (bus 0)
    // So we TX on main bus (bus 0)
    // GCOV_EXCL_START
    // Unreachable by design (allowlist pins VOLVO_PSCM to the main bus)
    if (msg->bus != VOLVO_MAIN_BUS) {
      tx = false;  // Wrong bus
    }
    // GCOV_EXCL_STOP
  }

  if (msg->addr == VOLVO_DRIVER_INPUT) {
    // Driver input message: we relay from party bus (bus 2) to main bus (bus 0)
    // So we TX on main bus (bus 0)
    // GCOV_EXCL_START
    // Unreachable by design (VOLVO_DRIVER_INPUT is not in VOLVO_TX_MSGS)
    if (msg->bus != VOLVO_MAIN_BUS) {
      tx = false;  // Wrong bus
    }
  }
  // GCOV_EXCL_STOP

  if (msg->addr == VOLVO_SAS) {
    // SAS message: we relay from party bus (bus 2) to main bus (bus 0)
    // So we TX on main bus (bus 0)
    // GCOV_EXCL_START
    // Unreachable by design (VOLVO_SAS is not in VOLVO_TX_MSGS)
    if (msg->bus != VOLVO_MAIN_BUS) {
      tx = false;  // Wrong bus
    }
  }
  // GCOV_EXCL_STOP

  if (msg->addr == VOLVO_LCA_2) {
    // LCA_2 -> PSCM
    // GCOV_EXCL_START
    // Unreachable by design (allowlist pins VOLVO_LCA_2 to the party bus)
    if (msg->bus != VOLVO_PARTY_BUS) {
      tx = false;  // Wrong bus
    }
    // GCOV_EXCL_STOP
  }

  return tx;
}

static safety_config volvo_init(uint16_t param) {
  bool spa = GET_FLAG(param, VOLVO_FLAG_SPA);
  volvo_c1 = GET_FLAG(param, VOLVO_FLAG_C1);

  if (volvo_c1) {
    static const CanMsg VOLVO_C1_TX_MSGS[] = {
      {VOLVO_C1_FSM_1, VOLVO_MAIN_BUS, 8, .check_relay = true},
      {VOLVO_C1_PSCM_1, VOLVO_PARTY_BUS, 8, .check_relay = true},
      {VOLVO_C1_BUTTONS, VOLVO_MAIN_BUS, 8, .check_relay = false},
    };
    static RxCheck volvo_c1_rx_checks[] = {
      {.msg = {{VOLVO_C1_PSCM_1, VOLVO_MAIN_BUS, 8, 50U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_C1_FSM_0, VOLVO_PARTY_BUS, 8, 100U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_C1_PEDAL_AND_BRAKE, VOLVO_MAIN_BUS, 8, 100U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_C1_SPEED, VOLVO_MAIN_BUS, 8, 50U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
    };
    return BUILD_SAFETY_CFG(volvo_c1_rx_checks, VOLVO_C1_TX_MSGS);
  }

  // Set PT bus addresses based on platform
  volvo_ecm_1_addr = spa ? VOLVO_SPA_ECM_1 : VOLVO_CMA_ECM_1;
  volvo_bus1_cruise_control_addr = spa ? VOLVO_SPA_BUS1_CRUISE_CONTROL : VOLVO_CMA_BUS1_CRUISE_CONTROL;

  // Define the TX messages needed to replace the stock LCA path. Payload
  // limits for steering and the PSCM relay are enforced in volvo_tx_hook.
  static const CanMsg VOLVO_TX_MSGS[] = {
    {VOLVO_LCA_STEER, VOLVO_PARTY_BUS, 8, .check_relay = true},  // LCA steering command to party bus
    {VOLVO_PSCM, VOLVO_MAIN_BUS, 8, .check_relay = true},  // PSCM message sent to main bus (relay from party bus)
    {VOLVO_LCA_3, VOLVO_PARTY_BUS, 8, .check_relay = true},  // LCA_3 message sent to party bus
    {VOLVO_LCA_2, VOLVO_PARTY_BUS, 8, .check_relay = true},  // LCA_2 message sent to party bus (spoof PILOT_ASSIST_ENGAGED for PSCM)
    {VOLVO_LCA_4, VOLVO_PARTY_BUS, 8, .check_relay = true},  // LCA_4 message sent to party bus (spoof LCA_ENABLE for PA state)
    {VOLVO_LCA_5, VOLVO_PARTY_BUS, 8, .check_relay = true},  // LCA_5 message sent to party bus (wheel speeds + LCA signals)
    {VOLVO_LCA_6, VOLVO_PARTY_BUS, 8, .check_relay = true},  // LCA_6 message sent to party bus
    {VOLVO_LCA_7, VOLVO_PARTY_BUS, 8, .check_relay = true},  // LCA_7 message sent to party bus
    //{VOLVO_SPEED, VOLVO_PARTY_BUS, 8, .check_relay = true},  // SPEED message sent to main bus
    //{VOLVO_SPEED_2, VOLVO_PARTY_BUS, 8, .check_relay = true},  // SPEED_2 message sent to main bus
    //{VOLVO_0x1a, VOLVO_PARTY_BUS, 8, .check_relay = true},  // 0x1a message sent to main bus
    //{VOLVO_GEAR_POSITION, VOLVO_PARTY_BUS, 8, .check_relay = true},  // GEAR_POSITION message sent from main to party bus
    //{VOLVO_EGSM, VOLVO_MAIN_BUS, 8, .check_relay = true},  // EGSM message sent from party to main bus
    {VOLVO_PSCM_RELATED, VOLVO_MAIN_BUS, 8, .check_relay = true},  // PSCM_RELATED message sent to party bus
  };

  // Define RX checks - PT bus addresses depend on CMA vs SPA
  safety_config ret;
  if (!spa) {
    static RxCheck volvo_rx_checks_cma[] = {
      {.msg = {{VOLVO_GEAR_POSITION, VOLVO_MAIN_BUS, 8, 40U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_LCA_2, VOLVO_MAIN_BUS, 8, 50U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_LCA_4, VOLVO_MAIN_BUS, 8, 29U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_LCA_6, VOLVO_MAIN_BUS, 8, 25U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_LCA_7, VOLVO_MAIN_BUS, 8, 29U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_SAS, VOLVO_PARTY_BUS, 8, 100U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_PSCM, VOLVO_PARTY_BUS, 8, 100U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_DRIVER_INPUT, VOLVO_PARTY_BUS, 8, 100U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_CMA_ECM_1, VOLVO_PT_BUS, 8, 17U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_LCA_STEER, VOLVO_MAIN_BUS, 8, 100U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_CMA_BUS1_CRUISE_CONTROL, VOLVO_PT_BUS, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_LCA_3, VOLVO_MAIN_BUS, 8, 67U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_LCA_5, VOLVO_MAIN_BUS, 8, 50U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_SPEED, VOLVO_MAIN_BUS, 8, 50U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_SPEED_2, VOLVO_MAIN_BUS, 8, 50U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_EGSM, VOLVO_PARTY_BUS, 8, 100U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_PSCM_RELATED, VOLVO_PARTY_BUS, 8, 100U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
    };
    ret = BUILD_SAFETY_CFG(volvo_rx_checks_cma, VOLVO_TX_MSGS);
  } else {
    static RxCheck volvo_rx_checks_spa[] = {
      {.msg = {{VOLVO_GEAR_POSITION, VOLVO_MAIN_BUS, 8, 40U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_LCA_2, VOLVO_MAIN_BUS, 8, 50U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_LCA_4, VOLVO_MAIN_BUS, 8, 29U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_LCA_6, VOLVO_MAIN_BUS, 8, 25U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_LCA_7, VOLVO_MAIN_BUS, 8, 29U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_SAS, VOLVO_PARTY_BUS, 8, 100U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_PSCM, VOLVO_PARTY_BUS, 8, 100U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_DRIVER_INPUT, VOLVO_PARTY_BUS, 8, 100U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_SPA_ECM_1, VOLVO_PT_BUS, 8, 100U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_LCA_STEER, VOLVO_MAIN_BUS, 8, 100U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      // true rate is 5Hz, but safety_tick invalidates checks declared <10Hz; lagging floor is 1s either way
      {.msg = {{VOLVO_SPA_BUS1_CRUISE_CONTROL, VOLVO_PT_BUS, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_LCA_3, VOLVO_MAIN_BUS, 8, 67U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_LCA_5, VOLVO_MAIN_BUS, 8, 50U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_SPEED, VOLVO_MAIN_BUS, 8, 50U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_SPEED_2, VOLVO_MAIN_BUS, 8, 50U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_EGSM, VOLVO_PARTY_BUS, 8, 100U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
      {.msg = {{VOLVO_PSCM_RELATED, VOLVO_PARTY_BUS, 8, 100U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
    };
    ret = BUILD_SAFETY_CFG(volvo_rx_checks_spa, VOLVO_TX_MSGS);
  }
  return ret;
}

const safety_hooks volvo_hooks = {
  .init = volvo_init,
  .rx = volvo_rx_hook,
  .tx = volvo_tx_hook,
  // No custom fwd hook - stock LCA always blocked by .check_relay = true
};
