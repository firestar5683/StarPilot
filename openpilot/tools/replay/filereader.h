#pragma once

#include <atomic>
#include <string>

class FileReader {
public:
  FileReader(bool cache_to_local, size_t max_bytes = 0) : cache_to_local_(cache_to_local), max_bytes_(max_bytes) {}
  virtual ~FileReader() {}
  std::string read(const std::string &file, std::atomic<bool> *abort = nullptr);

private:
  bool cache_to_local_;
  size_t max_bytes_;
};
