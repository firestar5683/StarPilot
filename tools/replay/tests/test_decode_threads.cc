#include <cassert>
#include <initializer_list>
#include "tools/replay/decode_threads.h"
int main() {
 assert(replay_decode_threads(nullptr) == 0);
 assert(replay_decode_threads("1") == 1);
 assert(replay_decode_threads("2") == 2);
 assert(replay_decode_threads("4") == 4);
 for (const char *value : {"", "0", "5", "-1", "2x", " 2", "2 ", "9999999999999999999"}) {
   assert(replay_decode_threads(value) == -1);
 }
}
