"""Build existing native replay sources into RoadScore, without altering openpilot."""
import subprocess,os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import capnproto,ffmpeg
root=Path('/data/openpilot');out=Path('/data/roadscore/native_build');out.mkdir(exist_ok=True)
gen=out/'cereal/gen/cpp';gen.mkdir(parents=True,exist_ok=True)
os.environ['PATH']=capnproto.BIN_DIR+':'+os.environ['PATH']
if not (gen/'log.capnp.h').exists() or any(p.stat().st_size==0 for p in gen.iterdir() if p.is_file()):subprocess.run(['capnpc','--src-prefix='+str(root/'cereal'),*map(str,(root/'cereal').glob('*.capnp')),'-o','c++:'+str(gen)],check=True)
includes=[out,root,root/'msgq_repo',root/'msgq_repo/msgq',root/'third_party',root/'third_party/opencl/include',root/'third_party/libyuv/include',root/'third_party/json11',root/'third_party/linux/include',Path(capnproto.INCLUDE_DIR),Path(ffmpeg.INCLUDE_DIR)]
flags=['clang++','-std=c++17','-O2','-fPIC','-D__TICI__','-DQCOM2','-Wno-deprecated-declarations']+['-I'+str(x) for x in includes]
replay=['main','replay','consoleui','camera','filereader','logreader','framereader','route','util','seg_mgr','timeline','api','qcom_decoder']
sources=[root/'tools/replay'/f'{x}.cc' for x in replay]
sources += [root/'msgq_repo/msgq'/f'{x}.cc' for x in ['ipc','event','impl_zmq','impl_msgq','impl_fake','msgq']]
sources += [root/'msgq_repo/msgq/visionipc'/f'{x}.cc' for x in ['visionipc','visionipc_server','visionipc_client','visionbuf','visionbuf_ion']]
sources+=list(gen.glob('*.c++'))+[root/'third_party/json11/json11.cpp']
def compile(src):
 obj=out/('_'.join(src.relative_to(root if src.is_relative_to(root) else out).parts)+'.o')
 if not obj.exists() or obj.stat().st_size==0 or obj.stat().st_mtime<src.stat().st_mtime:
  temporary=obj.with_suffix('.tmp.o')
  subprocess.run(flags+['-c',str(src),'-o',str(temporary)],check=True)
  temporary.replace(obj)
 return str(obj)
with ThreadPoolExecutor(max_workers=2) as pool:objects=list(pool.map(compile,sources))
libs=[str(root/'common/libcommon.a'),str(root/'cereal/libsocketmaster.a')]
libpaths=[ffmpeg.LIB_DIR,capnproto.LIB_DIR,str(root/'third_party/libyuv/larch64/lib'),'/system/vendor/lib64']
cmd=['clang++','-o',str(out/'replay.tmp'),*objects,*libs]+['-L'+x for x in libpaths]+['-Wl,-rpath,'+x for x in libpaths]+['-lavutil','-lavcodec','-lavformat','-lbz2','-lzstd','-lcurl','-lyuv','-lncurses','-lOpenCL','-lssl','-lcrypto','-lzmq','-lcapnp','-lkj','-lm','-lpthread']
subprocess.run(cmd,check=True)
(out/'replay.tmp').replace(out/'replay')
print(out/'replay')
