#pragma once

typedef struct {
  uint16_t sequence;
  uint16_t length;
  bool valid;
  uint8_t data[SPI_BUF_SIZE];
} spi_can_replay_t;

static spi_can_replay_t spi_can_replay;

static inline void spi_can_replay_reset(void) {
  spi_can_replay.valid = false;
}

static inline bool spi_can_write_sequenced(uint16_t sequence, const uint8_t *data, uint16_t length, bool *tx_ready) {
  bool accepted = false;
  if ((sequence != 0U) && (length > 0U) && (length < SPI_BUF_SIZE)) {
    if (spi_can_replay.valid && (sequence == spi_can_replay.sequence)) {
      // A lost reply must not turn an accepted CAN write into a second transmission.
      accepted = (length == spi_can_replay.length) && (memcmp(data, spi_can_replay.data, length) == 0);
    } else if (*tx_ready) {
      *tx_ready = false;
      comms_can_write(data, length);
      (void)memcpy(spi_can_replay.data, data, length);
      spi_can_replay.sequence = sequence;
      spi_can_replay.length = length;
      spi_can_replay.valid = true;
      accepted = true;
    } else {
    }
  }
  return accepted;
}
