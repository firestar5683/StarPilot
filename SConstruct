import os
import importlib
import shutil
import subprocess
import sys
import sysconfig
import platform
import numpy as np

import SCons.Errors

SCons.Warnings.warningAsException(True)

# pending upstream fix - https://github.com/SCons/scons/issues/4461
#SetOption('warn', 'all')

force_tici = os.environ.get("SP_FORCE_TICI", "").lower() in {"1", "true", "yes", "on"}
TICI = os.path.isfile('/TICI') or force_tici
AGNOS = TICI

Decider('MD5-timestamp')

SetOption('num_jobs', max(1, int(os.cpu_count()/2)))

AddOption('--kaitai',
          action='store_true',
          help='Regenerate kaitai struct parsers')

AddOption('--asan',
          action='store_true',
          help='turn on ASAN')

AddOption('--ubsan',
          action='store_true',
          help='turn on UBSan')

AddOption('--coverage',
          action='store_true',
          help='build with test coverage options')

AddOption('--ccflags',
          action='store',
          type='string',
          default='',
          help='pass arbitrary flags over the command line')

AddOption('--external-sconscript',
          action='store',
          metavar='FILE',
          dest='external_sconscript',
          help='add an external SConscript to the build')

AddOption('--mutation',
          action='store_true',
          help='generate mutation-ready code')

AddOption('--minimal',
          action='store_false',
          dest='extras',
          default=os.path.exists(File('#.lfsconfig').abspath), # minimal by default on release branch (where there's no LFS)
          help='the minimum build to run openpilot. no tests, tools, etc.')

AddOption('--extras',
          action='store_true',
          dest='extras',
          default=os.path.exists(File('#.lfsconfig').abspath),
          help='build optional tools/tests even when minimal is the default')

def maybe_delegate_to_laptop_device_builder() -> None:
  if platform.system() != "Darwin":
    return
  if os.environ.get("SP_FORCE_ARCH"):
    return
  if os.environ.get("SP_SKIP_CONTAINER_REEXEC"):
    return
  if os.environ.get("SP_DISABLE_AUTO_DEVICE_SCONS", "").lower() in {"1", "true", "yes", "on"}:
    return

  basedir = Dir("#").abspath
  sysroot_dir = os.environ.get("COMMA_SYSROOT_DIR", os.path.join(basedir, ".comma_sysroot"))
  required_sysroot_dirs = (
    "usr/local/lib",
    "lib/aarch64-linux-gnu",
    "usr/lib/aarch64-linux-gnu",
    "system/vendor/lib64",
  )
  if not all(os.path.isdir(os.path.join(sysroot_dir, p)) for p in required_sysroot_dirs):
    return

  docker_bin = shutil.which("docker")
  if docker_bin is None:
    mac_docker = "/Applications/Docker.app/Contents/Resources/bin/docker"
    if os.path.isfile(mac_docker):
      docker_bin = mac_docker

  if docker_bin is None and shutil.which("podman") is None:
    return

  builder = os.path.join(basedir, "scripts", "laptop_device_build.sh")
  if not os.path.isfile(builder):
    return

  print(f"Auto-routing scons to laptop device build (sysroot: {sysroot_dir})", flush=True)
  env = os.environ.copy()
  env["SP_SKIP_CONTAINER_REEXEC"] = "1"
  env.setdefault("COMMA_SYSROOT_DIR", sysroot_dir)
  if docker_bin is not None and shutil.which("docker") is None:
    docker_dir = os.path.dirname(docker_bin)
    env["PATH"] = f"{docker_dir}:{env.get('PATH', '')}"

  cmd = [builder, "build", *sys.argv[1:]]
  raise SystemExit(subprocess.call(cmd, cwd=basedir, env=env))

maybe_delegate_to_laptop_device_builder()

## Architecture name breakdown (arch)
## - larch64: linux tici aarch64
## - aarch64: linux pc aarch64
## - x86_64:  linux pc x64
## - Darwin:  mac x64 or arm64
real_arch = arch = subprocess.check_output(["uname", "-m"], encoding='utf8').rstrip()
forced_arch = os.environ.get("SP_FORCE_ARCH")
if forced_arch:
  arch = forced_arch
elif platform.system() == "Darwin":
  arch = "Darwin"
  brew_prefix = subprocess.check_output(['brew', '--prefix'], encoding='utf8').strip()
elif arch == "aarch64" and AGNOS:
  arch = "larch64"
assert arch in ["larch64", "aarch64", "x86_64", "Darwin"]

# AGNOS 19.6 ships native dependencies as versioned Python packages. Link
# Cap'n Proto statically from that managed package so release binaries don't
# depend on the removed libcapnp-1.0.2.so system library.
try:
  capnproto = importlib.import_module("capnproto")
except ModuleNotFoundError:
  capnproto = None
try:
  ffmpeg = importlib.import_module("ffmpeg")
except ModuleNotFoundError:
  ffmpeg = None

capnproto_include_dirs = [capnproto.INCLUDE_DIR] if capnproto is not None else []
capnproto_lib_dirs = [capnproto.LIB_DIR] if capnproto is not None else []
ffmpeg_include_dirs = [ffmpeg.INCLUDE_DIR] if ffmpeg is not None else []
ffmpeg_lib_dirs = [ffmpeg.LIB_DIR] if ffmpeg is not None else []

# Cross-builds install managed dependencies in /work/.venv-linux-arm64, but
# comma devices expose the same packages from /usr/local/venv. Never embed the
# host/container mount path in release binaries.
ffmpeg_runtime_lib_dirs = ffmpeg_lib_dirs
if arch == "larch64" and ffmpeg is not None:
  ffmpeg_runtime_lib_dirs = [os.path.join("/usr/local/venv", os.path.relpath(ffmpeg.LIB_DIR, sys.prefix))]

# The managed native-dependency packages keep their tools inside the package
# instead of installing them into /usr/local/venv/bin. cereal invokes capnpc
# directly while SConscript files are evaluated, so make the packaged tools
# discoverable to both SCons actions and configure-time subprocesses.
dependency_bin_dirs = [
  package.BIN_DIR for package in (capnproto, ffmpeg)
  if package is not None and os.path.isdir(package.BIN_DIR)
]
if dependency_bin_dirs:
  os.environ["PATH"] = os.pathsep.join([*dependency_bin_dirs, os.environ["PATH"]])

# Homebrew llvm can shadow Apple clang and break macOS SDK header resolution.
# Use the system toolchain explicitly on macOS for reliable local builds.
cc = '/usr/bin/clang' if arch == "Darwin" else 'clang'
cxx = '/usr/bin/clang++' if arch == "Darwin" else 'clang++'
ar = '/usr/bin/ar' if arch == "Darwin" else 'ar'
ranlib = '/usr/bin/ranlib' if arch == "Darwin" else 'ranlib'

lenv = {
  "PATH": os.environ['PATH'],
  "PYTHONPATH": ":".join([
    Dir("#").abspath,
    Dir("#third_party/acados").abspath,
    Dir("#opendbc_repo").abspath,
  ]),

  "ACADOS_SOURCE_DIR": Dir("#third_party/acados").abspath,
  "ACADOS_PYTHON_INTERFACE_PATH": Dir("#third_party/acados/acados_template").abspath,
  "TERA_PATH": Dir("#").abspath + f"/third_party/acados/{arch}/t_renderer"
}

# Allow callers to override cache/temp dirs used by subprocesses (e.g. tinygrad model compilation).
for key in ("HOME", "TMPDIR", "XDG_CACHE_HOME", "CACHEDB", "PARAMS_ROOT"):
  if key in os.environ:
    lenv[key] = os.environ[key]

rpath = []
arch_ldflags = []

def tici_libpath(path: str) -> str:
  tici_sysroot = os.environ.get("SP_TICI_SYSROOT", "").strip().rstrip("/")
  if arch != "larch64" or not tici_sysroot or not path.startswith("/"):
    return path
  return os.path.join(tici_sysroot, path.lstrip("/"))

if arch == "larch64":
  cpppath = [
    "#third_party/opencl/include",
    tici_libpath("/usr/local/include"),
    tici_libpath("/usr/include"),
    tici_libpath("/usr/include/aarch64-linux-gnu"),
  ]

  libpath = [
    tici_libpath("/usr/local/lib"),
    tici_libpath("/system/vendor/lib64"),
    f"#third_party/acados/{arch}/lib",
  ]

  libpath += [
    "#third_party/libyuv/larch64/lib",
    tici_libpath("/lib/aarch64-linux-gnu"),
    tici_libpath("/usr/lib/aarch64-linux-gnu")
  ]
  cflags = ["-D__TICI__", "-DQCOM2", "-mcpu=cortex-a57"]
  cxxflags = ["-D__TICI__", "-DQCOM2", "-mcpu=cortex-a57"]
  arch_ldflags += [
    f"-Wl,-rpath-link,{tici_libpath('/usr/local/lib')}",
    f"-Wl,-rpath-link,{tici_libpath('/lib/aarch64-linux-gnu')}",
    f"-Wl,-rpath-link,{tici_libpath('/usr/lib/aarch64-linux-gnu')}",
    f"-Wl,-rpath-link,{tici_libpath('/system/vendor/lib64')}",
    f"-Wl,-rpath-link,{tici_libpath('/vendor/lib64')}",
  ]
  # On non-aarch64 hosts (e.g. Docker on macOS), force clang cross-targeting.
  if platform.machine() not in ("aarch64", "arm64"):
    cross_target = os.environ.get("SP_CROSS_TARGET", "aarch64-linux-gnu")
    cflags += [f"--target={cross_target}"]
    cxxflags += [f"--target={cross_target}"]
    arch_ldflags += [f"--target={cross_target}"]
  rpath += ["/usr/local/lib"]
else:
  cflags = []
  cxxflags = []
  cpppath = []
  rpath += []

  # MacOS
  if arch == "Darwin":
    libpath = [
      f"#third_party/libyuv/{arch}/lib",
      f"#third_party/acados/{arch}/lib",
      f"{brew_prefix}/lib",
      f"{brew_prefix}/opt/openssl@3.0/lib",
      "/System/Library/Frameworks/OpenGL.framework/Libraries",
    ]

    cflags += ["-DGL_SILENCE_DEPRECATION"]
    cxxflags += ["-DGL_SILENCE_DEPRECATION"]
    cpppath += [
      f"{brew_prefix}/include",
      f"{brew_prefix}/opt/openssl@3.0/include",
    ]
  # Linux
  else:
    libpath = [
      f"#third_party/acados/{arch}/lib",
      f"#third_party/libyuv/{arch}/lib",
      "/usr/lib",
      "/usr/local/lib",
    ]

if GetOption('asan'):
  ccflags = ["-fsanitize=address", "-fno-omit-frame-pointer"]
  ldflags = ["-fsanitize=address"]
elif GetOption('ubsan'):
  ccflags = ["-fsanitize=undefined"]
  ldflags = ["-fsanitize=undefined"]
else:
  ccflags = []
  ldflags = []
ldflags += arch_ldflags

# AGNOS devices are memory-constrained during on-device C++ compiles.
# Building without debug symbols dramatically reduces peak clang memory and
# prevents lowmemorykiller SIGKILLs (Error -9) on large translation units.
use_debug_symbols = os.environ.get("SP_FORCE_DEBUG_SYMBOLS", "").lower() in {"1", "true", "yes", "on"}
debug_flag = "-g" if (not AGNOS or use_debug_symbols) else "-g0"

# no --as-needed on mac linker
if arch != "Darwin":
  ldflags += ["-Wl,--as-needed", "-Wl,--no-undefined"]

ccflags_option = GetOption('ccflags')
if ccflags_option:
  ccflags += ccflags_option.split(' ')

env = Environment(
  ENV=lenv,
  CCFLAGS=[
    debug_flag,
    "-fPIC",
    "-O2",
    "-Wunused",
    "-Werror",
    "-Wshadow",
    "-Wno-unknown-warning-option",
    "-Wno-inconsistent-missing-override",
    "-Wno-c99-designator",
    "-Wno-reorder-init-list",
    "-Wno-vla-cxx-extension",
  ] + cflags + ccflags,

  # Managed dependencies must precede the compatibility sysroot. The sysroot
  # can intentionally retain legacy libraries for C3 support, but new release
  # binaries must link against the versions shipped in the managed venv.
  CPPPATH=capnproto_include_dirs + ffmpeg_include_dirs + cpppath + [
    "#",
    "#third_party/acados/include",
    "#third_party/acados/include/blasfeo/include",
    "#third_party/acados/include/hpipm/include",
    "#third_party/catch2/include",
    "#third_party/libyuv/include",
    "#third_party/json11",
    "#third_party/linux/include",
    "#third_party",
    "#msgq",
  ],

  CC=cc,
  CXX=cxx,
  AR=ar,
  RANLIB=ranlib,
  LINKFLAGS=ldflags,

  RPATH=ffmpeg_runtime_lib_dirs + rpath,

  CFLAGS=["-std=gnu11"] + cflags,
  CXXFLAGS=["-std=c++1z"] + cxxflags,
  LIBPATH=capnproto_lib_dirs + ffmpeg_lib_dirs + libpath + [
    "#msgq_repo",
    "#third_party",
    "#selfdrive/pandad",
    "#common",
    "#rednose/helpers",
  ],
  CYTHONCFILESUFFIX=".cpp",
  COMPILATIONDB_USE_ABSPATH=True,
  REDNOSE_ROOT="#",
  tools=["default", "cython", "compilation_db", "rednose_filter"],
  toolpath=["#site_scons/site_tools", "#rednose_repo/site_scons/site_tools"],
)

if arch == "Darwin":
  # RPATH is not supported on macOS, instead use the linker flags
  darwin_rpath_link_flags = [f"-Wl,-rpath,{path}" for path in env["RPATH"]]
  env["LINKFLAGS"] += darwin_rpath_link_flags

env.CompilationDatabase('compile_commands.json')

# Setup cache dir
cache_dir = os.environ.get("SP_SCONS_CACHE_DIR", "").strip()
if not cache_dir:
  cache_dir = '/data/scons_cache' if AGNOS else '/tmp/scons_cache'
CacheDir(cache_dir)
Clean(["."], cache_dir)

node_interval = 5
node_count = 0
def progress_function(node):
  global node_count
  node_count += node_interval
  sys.stderr.write("progress: %d\n" % node_count)

if os.environ.get('SCONS_PROGRESS'):
  Progress(progress_function, interval=node_interval)

# Cython build environment
py_include = sysconfig.get_paths()['include']
if arch == "larch64" and platform.machine() not in ("aarch64", "arm64"):
  tici_py_include = tici_libpath(f"/usr/include/python{sys.version_info.major}.{sys.version_info.minor}")
  if os.path.isdir(tici_py_include):
    py_include = tici_py_include
envCython = env.Clone()
envCython["CPPPATH"] += [py_include, np.get_include()]
envCython["CCFLAGS"] += ["-Wno-#warnings", "-Wno-shadow", "-Wno-deprecated-declarations"]
envCython["CCFLAGS"].remove("-Werror")

envCython["LIBS"] = []
if arch == "Darwin":
  envCython["LINKFLAGS"] = ["-bundle", "-undefined", "dynamic_lookup"] + darwin_rpath_link_flags
else:
  envCython["LINKFLAGS"] = arch_ldflags + ["-pthread", "-shared"]

np_version = SCons.Script.Value(np.__version__)
Export('envCython', 'np_version')

Export('env', 'arch', 'real_arch')

# Build common module
SConscript(['common/SConscript'])
Import('_common', '_gpucommon')

common = [_common, 'json11', 'zmq']
gpucommon = [_gpucommon]

Export('common', 'gpucommon')

# Build messaging (cereal + msgq + socketmaster + their dependencies)
# Enable swaglog include in submodules
env_swaglog = env.Clone()
env_swaglog['CXXFLAGS'].append('-DSWAGLOG="\\"common/swaglog.h\\""')
SConscript(['msgq_repo/SConscript'], exports={'env': env_swaglog})
SConscript(['opendbc_repo/SConscript'], exports={'env': env_swaglog})

SConscript(['cereal/SConscript'])

Import('socketmaster', 'msgq')
if capnproto is not None:
  messaging = [
    socketmaster,
    msgq,
    File(os.path.join(capnproto.LIB_DIR, "libcapnp.a")),
    File(os.path.join(capnproto.LIB_DIR, "libkj.a")),
  ]
else:
  messaging = [socketmaster, msgq, 'capnp', 'kj']
Export('messaging')


# Build other submodules
SConscript(['panda/SConscript'])

# Build rednose library
SConscript(['rednose/SConscript'])

# Build system services
SConscript([
  'system/ubloxd/SConscript',
  'system/loggerd/SConscript',
])

if arch == "larch64":
  SConscript(['system/camerad/SConscript'])

# Build openpilot
SConscript(['third_party/SConscript'])

SConscript(['selfdrive/SConscript'])

if Dir('#tools/cabana/').exists() and GetOption('extras'):
  SConscript(['tools/replay/SConscript'])
  if arch != "larch64":
    SConscript(['tools/cabana/SConscript'])

external_sconscript = GetOption('external_sconscript')
if external_sconscript:
  SConscript([external_sconscript])
