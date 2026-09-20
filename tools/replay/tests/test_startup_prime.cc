#include <cassert>
#include "tools/replay/startup_prime.h"
int main() {
 std::vector<int> route{0,1,2,3,4,5,6,7};
 assert(!startup_cache_ready(route,{2},2,5));
 assert(!startup_cache_ready(route,{2,3,4},2,5));
 assert(startup_cache_ready(route,{0,1,2,3,4},2,5));
 assert(!startup_cache_ready(route,{0,1,2,3,4},7,5));
 assert(startup_cache_ready(route,{3,4,5,6,7},7,5));
 assert(startup_cache_ready({0,1},{0,1},0,5));
 assert(!startup_cache_ready({0,2,3},{0,2},2,5));
 assert(startup_cache_ready({0,2,3},{0,2,3},2,5));
 assert(!startup_cache_ready(route,{0,1,2,3,4},2,0));
}
