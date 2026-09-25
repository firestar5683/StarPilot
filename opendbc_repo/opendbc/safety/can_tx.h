#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "opendbc/safety/can.h"

void can_set_checksum(CANPacket_t *packet);
void can_send(CANPacket_t *to_push, uint8_t bus_number, bool skip_tx_hook);
