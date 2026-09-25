package gomsgq

// #include <stdint.h>
// #include <signal.h>
//
// static void thread_signal(unsigned int tid) {
//   #ifdef __APPLE__
//     // macOS doesn't have tkill, rely on polling instead
//     (void)tid;
//   #elif !defined(SYS_tkill)
//     // fallback for systems without tkill
//     kill(tid, SIGUSR2);
//   #else
//     syscall(SYS_tkill, tid, SIGUSR2);
//   #endif
// }
import "C"

func ThreadSignal(tid uint32) {
	C.thread_signal(C.uint(tid))
}
