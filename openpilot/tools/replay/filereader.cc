#include "tools/replay/filereader.h"

#include <fstream>
#include <unistd.h>
#include <filesystem>

#include "common/util.h"
#include "tools/replay/py_tools.h"

std::string FileReader::read(const std::string &file, std::atomic<bool> *abort) {
  if (abort && *abort) return {};
  auto read_bounded = [&](const std::string &path) {
    std::ifstream source(path, std::ios::binary);
    std::string data;
    char chunk[65536];
    while (source && !(abort && *abort)) {
      source.read(chunk, sizeof(chunk));
      const auto count = source.gcount();
      if (max_bytes_ && data.size() + count > max_bytes_) return std::string{};
      data.append(chunk, count);
    }
    return source.bad() || (abort && *abort) ? std::string{} : data;
  };
  const bool is_remote = (file.find("https://") == 0) || (file.find("http://") == 0);
  if (is_remote) {
    std::string local_path = PyTools::download(file, cache_to_local_, abort);
    if (local_path.empty()) return {};
    return read_bounded(local_path);
  }
  char header[4] = {};
  std::ifstream stream(file, std::ios::binary);
  stream.read(header, sizeof(header));
  const std::string magic(header, stream.gcount());
  if (util::ends_with(file, ".bz2") || util::ends_with(file, ".zst") ||
      util::starts_with(magic, "BZh") || magic == "\x28\xB5\x2F\xFD") {
    std::string local_path = PyTools::decompress(file, abort, max_bytes_);
    if (local_path.empty()) return {};
    std::string data = read_bounded(local_path);
    unlink(local_path.c_str());
    return data;
  }
  return read_bounded(file);
}
