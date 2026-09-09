// Host-only fixtures. No CAN transmission, target access, or firmware image.
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "opendbc/safety/can.h"
typedef struct {} harness_configuration;
typedef struct {} GPIO_TypeDef;
#include "board/boards/board_declarations.h"
#define HARNESS_STATUS_NC 0U
#define HARNESS_STATUS_FLIPPED 2U
#define LED_GREEN 1U
#define LED_BLUE 2U
#define POWER_SAVE_STATUS_ENABLED 1U
#define FAULT_RELAY_MALFUNCTION 1U
#define SAFETY_SILENT 0U
#define SAFETY_NOOUTPUT 19U
#define SAFETY_ALLOUTPUT 17U
#define SAFETY_ELM327 3U
struct { uint32_t SR; } timer;
#define TICK_TIMER (&timer)
struct { uint8_t status; } harness;
struct { uint16_t w_ptr_tx; } uart_ring_som_debug;
struct { uint32_t r_ptr, w_ptr; } can_rx_q, can_tx1_q, can_tx2_q, can_tx3_q;
bool line, som_gpio, gm_remote_start_boots_comma;
bool siren_enabled, relay_malfunction, controls_allowed, heartbeat_engaged;
bool heartbeat_disabled, heartbeat_lost;
uint32_t heartbeat_counter, heartbeat_engaged_mismatches, uptime_cnt, safety_mode_cnt;
uint16_t current_safety_mode = 42U, current_safety_param;
uint8_t power_save_status;
int current_safety_config;
unsigned watchdog_kicks, safety_ticks, silent_calls, ir_calls, fan_power, register_checks;
BootState observed_boot;
unsigned gpio_calls;
bool gpio_level;
#define GPIOA ((GPIO_TypeDef *)1)
void set_gpio_output(GPIO_TypeDef *port, unsigned pin, bool value) {
  assert(port == GPIOA && pin == 0U); gpio_calls++; gpio_level = value;
}
static void cuatro_set_bootkick(BootState state);
void boot_output(BootState state) { observed_boot = state; cuatro_set_bootkick(state); }
bool read_som(void) { return som_gpio; }
void bool_sink(bool x) { (void)x; }
void ir_output(uint8_t x) { assert(x == 0U); ir_calls++; }
struct board fixture_board = {.set_bootkick=boot_output, .read_som_gpio=read_som,
  .set_siren=bool_sink, .set_ir_power=ir_output};
struct board *current_board = &fixture_board;
bool harness_check_ignition(void) { return line; }
void fan_tick(void) {}
void harness_tick(void) {}
void sound_tick(void) {}
void simple_watchdog_kick(void) { watchdog_kicks++; }
void fault_occurred(unsigned x) { (void)x; }
void fault_recovered(unsigned x) { (void)x; }
void can_set_orientation(bool x) { (void)x; }
void can_init_all(void) {}
void set_safety_mode(uint16_t mode, uint16_t param) {
  current_safety_mode = mode; current_safety_param = param;
  if (mode == SAFETY_SILENT) silent_calls++;
}
void set_power_save_state(uint8_t x) { power_save_status = x; }
void led_set(unsigned x, bool y) { (void)x; (void)y; }
void print(const char *x) { (void)x; }
void puth(unsigned x) { (void)x; }
void puth4(unsigned x) { (void)x; }
void fan_set_power(unsigned x) { fan_power = x; }
void check_registers(void) { register_checks++; }
void safety_tick(int *x) { (void)x; safety_ticks++; }
