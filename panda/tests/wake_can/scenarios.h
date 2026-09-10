// Included after verbatim production functions. Each scenario gets a fresh process.
static void tick(void) { timer.SR = 1U; tick_handler(); }
static void second(void) { for (int i=0; i<8; i++) tick(); }
static CANPacket_t packet(unsigned bus, unsigned addr, unsigned dlc, unsigned state, unsigned counter) {
  CANPacket_t p = {0}; p.bus=bus; p.addr=addr; p.data_len_code=dlc;
  p.data[0]=state<<5; p.data[6]=counter<<4;
  // Tesla DBC checksum: address bytes plus seven payload bytes, modulo 256.
  unsigned sum=(addr & 255U)+(addr >> 8U);
  for (unsigned i=0; i<7; i++) sum+=p.data[i];
  p.data[7]=sum & 255U;
  return p;
}
static void tesla(unsigned state, unsigned counter) {
  CANPacket_t p=packet(0,0x221,8,state,counter); ignition_can_hook(&p);
}
static void pair(unsigned state) { tesla(state,14); tesla(state,15); }
static void wake_case(void) {
  assert(!wake_on_can && !ignition_can);
  tesla(2,14); assert(!wake_on_can && !ignition_can); // prime only
  for (unsigned state=0; state<4; state++) {
    tesla(state,(15+state)%16);
    assert(wake_on_can == (state != 0)); assert(ignition_can == (state == 3));
    assert(wake_on_can_cnt == 0 && ignition_can_cnt == 0);
  }
  tesla(0,3); assert(!wake_on_can && !ignition_can); // accepted OFF clears immediately
}
static void invalid_case(void) {
  pair(2); assert(wake_on_can); wake_on_can_cnt=2;
  for (unsigned bus=1; bus<8; bus++) {
    CANPacket_t p=packet(bus,0x221,8,0,0); ignition_can_hook(&p);
    assert(wake_on_can && wake_on_can_cnt == 2);
  }
  for (unsigned dlc=0; dlc<16; dlc++) {
    if (dlc==8) continue;
    CANPacket_t p=packet(0,0x221,dlc,0,0); ignition_can_hook(&p);
    assert(wake_on_can && wake_on_can_cnt==2);
  }
  CANPacket_t p=packet(0,0x220,8,0,0); ignition_can_hook(&p);
  assert(wake_on_can && wake_on_can_cnt==2);
  tesla(0,15); assert(wake_on_can && wake_on_can_cnt==2); // duplicate
  tesla(0,7); assert(wake_on_can && wake_on_can_cnt==2); // jump
  tesla(0,8); assert(!wake_on_can && wake_on_can_cnt==0); // reacquire after jump
  tesla(2,9); assert(wake_on_can);
  wake_on_can_cnt=2;
  p=packet(0,0x221,8,2,10); p.data[7]^=1; ignition_can_hook(&p);
  assert(wake_on_can && wake_on_can_cnt==2); // invalid frames cannot refresh wake
  tesla(0,11); assert(wake_on_can && wake_on_can_cnt==2); // valid frame primes again
  tesla(0,12); assert(!wake_on_can && wake_on_can_cnt==0);
}

static void disabled_case(void) {
  for (unsigned state=0; state<4; state++) {
    pair(state);
    assert(!wake_on_can); // default and other manufacturers never gain Tesla wake
    assert(ignition_can == (state==3)); // stock DRIVE remains independent of opt-in
  }
}
static void checksum_case(void) {
  CANPacket_t p=packet(0,0x221,8,2,14);
  assert(p.data[7]==0x43); // address 0x23 + ACCESSORY 0x40 + counter 0xE0
  p.data[7]^=1; ignition_can_hook(&p);
  tesla(2,15); assert(!wake_on_can); // bad checksum cannot prime a wake
  tesla(2,0); assert(wake_on_can); // two valid consecutive frames, including wrap
  tesla(0,1); assert(!wake_on_can);
  // Corruption in any payload/checksum byte cannot create a wake or prime it.
  for (unsigned i=0; i<8; i++) {
    p=packet(0,0x221,8,2,2); p.data[i]^=1; ignition_can_hook(&p);
    assert(!wake_on_can);
    tesla(2,3); assert(!wake_on_can);
    tesla(0,4); assert(!wake_on_can);
  }
  p=packet(0,0x221,8,2,5); p.extended=1; ignition_can_hook(&p);
  assert(!wake_on_can);
  tesla(2,6); assert(!wake_on_can);
  tesla(2,7); assert(wake_on_can);
  wake_on_can_cnt=2;
  for (unsigned i=0; i<4; i++) {
    p=packet(0,0x221,8,2,8+i); p.data[7]^=1; ignition_can_hook(&p);
    second();
  }
  assert(!wake_on_can); // checksum-invalid traffic ages out
  // Do not change the stock DRIVE decoder while hardening the extra wake path.
  p=packet(0,0x221,8,3,12); p.data[7]^=1; ignition_can_hook(&p);
  assert(ignition_can && !wake_on_can);
}

static void stale_case(void) {
  pair(2);
  for (unsigned i=1; i<=3; i++) { second(); assert(wake_on_can && wake_on_can_cnt==i); }
  second(); assert(!wake_on_can && wake_on_can_cnt==4);
  // Staleness does not reset the decoder's static previous counter (reference parity).
  tesla(2,15); assert(!wake_on_can && wake_on_can_cnt==4);
  tesla(2,0); assert(wake_on_can && wake_on_can_cnt==0); // wrap after stale
  second(); assert(wake_on_can_cnt==1);
  tesla(0,1); assert(!wake_on_can && wake_on_can_cnt==0);
  wake_on_can_cnt=UINT32_MAX; second(); assert(!wake_on_can && wake_on_can_cnt==0);
}
static void watchdog_case(void) {
  pair(2); assert(wake_on_can && !ignition_can);
  heartbeat_disabled=true; controls_allowed=true; heartbeat_engaged=true; som_gpio=true;
  second(); assert(heartbeat_counter==1 && !heartbeat_disabled && !heartbeat_lost);
  second(); assert(heartbeat_counter==2 && heartbeat_lost && !heartbeat_engaged);
  assert(current_safety_mode==SAFETY_SILENT && silent_calls==1);
  assert(power_save_status==POWER_SAVE_STATUS_ENABLED && ir_calls==1 && fan_power==30);
  assert(watchdog_kicks==16 && safety_ticks==2 && register_checks==2);
  heartbeat_counter=UINT32_MAX; second(); assert(heartbeat_counter==UINT32_MAX);
}
static void drive_watchdog_case(void) {
  pair(3);
  for (unsigned i=1; i<5; i++) {
    tesla(3,(15+i)%16); second(); assert(!heartbeat_lost && heartbeat_counter==i);
  }
  tesla(3,4); second(); assert(heartbeat_counter==5 && heartbeat_lost);
}
static void boot_case(void) {
  legacy_bootkick(false,false); assert(observed_boot==BOOT_BOOTKICK); // first power-on
  for (int i=0; i<30; i++) legacy_bootkick(false,false);
  assert(!bootkick_reset_triggered); // no first-boot reset
  legacy_bootkick(false,true); assert(observed_boot==BOOT_STANDBY);
  legacy_bootkick(true,false); assert(observed_boot==BOOT_BOOTKICK);
  for (int i=0; i<18; i++) { legacy_bootkick(true,false); assert(observed_boot==BOOT_BOOTKICK); }
  legacy_bootkick(true,false); assert(observed_boot==BOOT_RESET && bootkick_reset_triggered);
  assert(gpio_level); // Cuatro RESET is deasserted bootkick, NOT a separate reset pin
  for (int i=0; i<4; i++) { legacy_bootkick(true,false); assert(observed_boot==BOOT_RESET); }
  legacy_bootkick(true,false); assert(observed_boot==BOOT_BOOTKICK && !gpio_level);
  legacy_bootkick(false,true); legacy_bootkick(true,false);
  for (int i=0; i<30; i++) legacy_bootkick(true,false);
  assert(observed_boot==BOOT_BOOTKICK); // only one reset per MCU boot
}
static void cancel_reset_case(int serial) {
  legacy_bootkick(false,true); legacy_bootkick(true,false);
  if (serial) uart_ring_som_debug.w_ptr_tx++; else som_gpio=true;
  legacy_bootkick(true,false); som_gpio=false;
  for (int i=0; i<30; i++) legacy_bootkick(true,false);
  assert(!bootkick_reset_triggered && observed_boot==BOOT_BOOTKICK);
}
static void existing_case(void) {
  // Harness insertion still wakes with ignition false.
  legacy_bootkick(false,true); harness.status=1;
  legacy_bootkick(false,false); assert(observed_boot==BOOT_BOOTKICK);
  legacy_bootkick(false,true); assert(observed_boot==BOOT_STANDBY);
  line=true; heartbeat_counter=1; second();
#ifdef PANDA_IGNORE_IGNITION_LINE
  assert(observed_boot==BOOT_STANDBY);
#else
  assert(observed_boot==BOOT_BOOTKICK);
#endif
}
static void other_cars_case(void) {
  CANPacket_t p=packet(0,0x1F1,8,0,0); p.data[0]=2; ignition_can_hook(&p);
#ifdef PANDA_GM_REMOTE_START_C9
  assert(!ignition_can);
#else
  assert(ignition_can);
#endif
  gm_remote_start_boots_comma=true;
  p=packet(0,0xC9,8,0,0); p.data[6]=0x10; ignition_can_hook(&p); assert(ignition_can);
  p.data[6]=0; ignition_can_hook(&p); assert(!ignition_can);
  // Pre-AP checksum and counter remain active.
  p=packet(0,0x101,3,0,0); p.data[0]=8; p.data[1]=14; p.data[2]=24; ignition_can_hook(&p);
  assert(!ignition_can); p.data[1]=15; p.data[2]=25; ignition_can_hook(&p); assert(ignition_can);
  p.data[0]=0; p.data[1]=0; p.data[2]=99; ignition_can_hook(&p); assert(ignition_can);
  p.data[1]=1; p.data[2]=3; ignition_can_hook(&p); assert(!ignition_can);
  // Rivian sequential modulo-15, then Mazda.
  p=packet(0,0x152,8,0,0); p.data[1]=14; p.data[7]=0x10; ignition_can_hook(&p);
  assert(!ignition_can); p.data[1]=0; ignition_can_hook(&p); assert(ignition_can);
  p=packet(0,0x9E,8,0,0); ignition_can_hook(&p); assert(!ignition_can);
  p.data[0]=0xC0; ignition_can_hook(&p); assert(ignition_can);
  assert(!wake_on_can); // none of these set Tesla-only wake flag
#ifdef PANDA_HKG_REMOTE_START
  ignition_can=false; legacy_bootkick(false,true);
  p=packet(1,0x384,8,0,0); p.data[3]=1; ignition_can_hook(&p);
  assert(hkg_remote_climate_wake && !ignition_can && !wake_on_can);
  heartbeat_counter=1; second(); assert(observed_boot==BOOT_BOOTKICK && !heartbeat_lost);
  for (int i=0; i<3; i++) second();
  assert(!hkg_remote_climate_wake && hkg_remote_climate_wake_cnt==4);
#endif
}
static void drive_edge_case(void) {
  // Prolonged awake, SOM shuts down while fresh ACCESSORY CAN continues.
  pair(2); second(); heartbeat_counter=0; second(); assert(observed_boot==BOOT_STANDBY);
  for (unsigned i=0; i<3700; i++) { tesla(2,i%16); second(); }
  assert(wake_on_can && !ignition_can && observed_boot==BOOT_STANDBY);
  tesla(3,4); second(); assert(ignition_can && wake_on_can);
  assert(observed_boot==BOOT_BOOTKICK); // Stock DRIVE edge must survive held wake.
  puts("PASS: fresh ACCESSORY through SOM shutdown preserves later DRIVE bootkick");
  tesla(0,5); second(); tesla(2,6); second();
  assert(observed_boot==BOOT_BOOTKICK); // true low->high recovers
  heartbeat_counter=0; second(); assert(observed_boot==BOOT_STANDBY);
  // Car sleep / absent or rejected traffic must age wake out and permit re-wake.
  for (unsigned i=0; i<5; i++) {
    tesla(2,6); // repeated counter cannot keep the wake fresh
    second();
  }
  assert(!wake_on_can && !ignition_can && observed_boot==BOOT_STANDBY);
  tesla(2,7); second(); assert(wake_on_can && observed_boot==BOOT_BOOTKICK);
}
static void stock_drive_case(void) {
  // This exact physical-input sequence passes both stock and candidate.
  pair(2); second(); heartbeat_counter=0; second();
  for (unsigned i=0; i<3700; i++) { tesla(2,i%16); second(); }
  assert(!ignition_can && observed_boot==BOOT_STANDBY);
  tesla(3,4); second();
  assert(ignition_can && observed_boot==BOOT_BOOTKICK);
}
static void independent_edges_case(void) {
  test_bootkick(false,true,false); assert(observed_boot==BOOT_STANDBY);
  test_bootkick(false,true,true); assert(observed_boot==BOOT_BOOTKICK); // edge beats heartbeat
  test_bootkick(false,true,true); assert(observed_boot==BOOT_STANDBY);
  test_bootkick(false,false,true); assert(observed_boot==BOOT_STANDBY); // held wake is not level-triggered
  test_bootkick(true,true,true); assert(observed_boot==BOOT_BOOTKICK); // independent ignition edge
  test_bootkick(true,true,false); assert(observed_boot==BOOT_STANDBY);
  test_bootkick(true,false,true); assert(observed_boot==BOOT_STANDBY); // no new wake kick while started
  test_bootkick(false,false,true); assert(observed_boot==BOOT_STANDBY); // falling ignition is not wake edge
  test_bootkick(false,false,false); assert(observed_boot==BOOT_STANDBY);
  test_bootkick(false,false,true); assert(observed_boot==BOOT_BOOTKICK);
  test_bootkick(false,true,true); assert(observed_boot==BOOT_STANDBY);
  harness.status=1;
  test_bootkick(false,true,true); assert(observed_boot==BOOT_BOOTKICK); // harness still beats heartbeat
}
static void wake_reset_case(void) {
  test_bootkick(false,true,false);
  test_bootkick(false,false,true);
  for (int i=0; i<18; i++) { test_bootkick(false,false,true); assert(observed_boot==BOOT_BOOTKICK); }
  test_bootkick(false,false,true); assert(observed_boot==BOOT_RESET && bootkick_reset_triggered);
  // Ignition, wake, harness and heartbeat cannot interrupt the active reset.
  for (int i=0; i<4; i++) {
    harness.status=(i%2)+1;
    test_bootkick(i%2,true,i%2); assert(observed_boot==BOOT_RESET);
  }
  test_bootkick(true,false,true); assert(observed_boot==BOOT_BOOTKICK);
  test_bootkick(false,true,false); test_bootkick(false,false,true);
  for (int i=0; i<30; i++) test_bootkick(false,false,true);
  assert(observed_boot==BOOT_BOOTKICK); // no second reset
}
static void boot_trace_case(void) {
  uint32_t rng=0x87654321;
  for (unsigned i=0; i<20000; i++) {
    rng=rng*1664525U+1013904223U;
    if (i%37==0) harness.status=(rng>>20)%3;
    if (i%53==0) uart_ring_som_debug.w_ptr_tx++;
    som_gpio=(rng%97)==0;
    legacy_bootkick((rng>>30)!=0,(rng%29)==0);
    printf("%u %u %u %u %u\n",i,observed_boot,bootkick_reset_triggered,gpio_level,gpio_calls);
  }
}
static void trace_case(void) {
  uint32_t rng=0x12345678;
  const unsigned ids[]={0x221,0x101,0x152,0x1F1,0xC9,0x9E,0x384,0x220};
  for (unsigned i=0; i<20000; i++) {
    rng=rng*1664525U+1013904223U;
    CANPacket_t p=packet((rng>>29)%3,ids[(rng>>20)%8],(rng>>8)%16,(rng>>2)%4,i%16);
    for (unsigned b=0;b<8;b++) p.data[b]=(rng>>(b*3))&255;
    if ((i%3)==0) p=packet(0,0x221,8,i%4,i%16);
    line=(rng&255)==0; gm_remote_start_boots_comma=(rng&256)!=0;
    if ((i%17)==0) { heartbeat_counter=0; current_safety_mode=42; controls_allowed=true; heartbeat_engaged=true; }
    ignition_can_hook(&p); tick();
    printf("%u %u %u %u %u %u %u %u %u %u %u %u %u\n",i,ignition_can,ignition_can_cnt,heartbeat_counter,
      current_safety_mode,heartbeat_lost,heartbeat_engaged,controls_allowed,heartbeat_engaged_mismatches,
      power_save_status,watchdog_kicks,safety_ticks,ir_calls);
  }
}
int main(int argc,char **argv) {
  assert(argc==2);
  if (!strcmp(argv[1],"disabled")) disabled_case();
  else if (!strcmp(argv[1],"checksum")) checksum_case();
  else if (!strcmp(argv[1],"states")) wake_case();
  else if (!strcmp(argv[1],"invalid")) invalid_case();
  else if (!strcmp(argv[1],"stale")) stale_case();
  else if (!strcmp(argv[1],"watchdog")) watchdog_case();
  else if (!strcmp(argv[1],"drive_watchdog")) drive_watchdog_case();
  else if (!strcmp(argv[1],"boot")) boot_case();
  else if (!strcmp(argv[1],"serial")) cancel_reset_case(1);
  else if (!strcmp(argv[1],"gpio")) cancel_reset_case(0);
  else if (!strcmp(argv[1],"existing")) existing_case();
  else if (!strcmp(argv[1],"other_cars")) other_cars_case();
  else if (!strcmp(argv[1],"drive_edge")) drive_edge_case();
  else if (!strcmp(argv[1],"stock_drive")) stock_drive_case();
  else if (!strcmp(argv[1],"independent_edges")) independent_edges_case();
  else if (!strcmp(argv[1],"wake_reset")) wake_reset_case();
  else if (!strcmp(argv[1],"boot_trace")) boot_trace_case();
  else if (!strcmp(argv[1],"trace")) trace_case();
  else return 2;
  return 0;
}
