#pragma once

// Only the selected GM owner uses this storage. Each owning initializer replaces
// every entry from its immutable template, including all runtime RX status.
static RxCheck gm_extended_rx_checks[10];
