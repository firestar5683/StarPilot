#include "system/camerad/cameras/camera_common.h"

#include "common/params.h"
#include "common/swaglog.h"
#include "common/util.h"

int main(int argc, char *argv[]) {
  // doesn't need RT priority since we're using isolcpus
  int ret = util::set_core_affinity({6});
  if (ret != 0 && !Params().getBool("IsOffroad")) {
    // Keep camerad alive in forced/demo bring-up scenarios where affinity can fail.
    LOGW("camerad: set_core_affinity failed (%d), continuing", ret);
  }

  if (Params().getBool("DisableWideRoad")) {
    setenv("DISABLE_WIDE_ROAD", "1", 1);
    LOGW("camerad: DisableWideRoad param set, disabling wide road camera");
  }

  camerad_thread();
  return 0;
}
