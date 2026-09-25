package cereal

/*
#include <time.h>
#ifdef __APPLE__
#include <mach/mach_time.h>
#define CLOCK_BOOTTIME CLOCK_MONOTONIC
#endif
static unsigned long long get_nsecs(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_BOOTTIME, &ts);
    return (unsigned long long)ts.tv_sec * 1000000000UL + ts.tv_nsec;
}
static unsigned long long get_monotonic_nsecs(void)
{
#ifdef __APPLE__
    // CPython time.monotonic() uses mach_absolute_time on macOS, whose epoch
    // differs from clock_gettime(CLOCK_MONOTONIC) on this host.
    mach_timebase_info_data_t scale;
    if (mach_timebase_info(&scale) != 0 || scale.denom == 0) return 0;
    return (unsigned long long)(((__uint128_t)mach_absolute_time() * scale.numer) / scale.denom);
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (unsigned long long)ts.tv_sec * 1000000000UL + ts.tv_nsec;
#endif
}
*/
import "C"

func GetTime() uint64 {
	return uint64(C.get_nsecs())
}

// Python GPS publishers use messaging.new_message, whose Event.logMonoTime
// comes from CLOCK_MONOTONIC rather than the BOOTTIME used by Mapd output.
func GetMonotonicTime() uint64 {
	return uint64(C.get_monotonic_nsecs())
}
