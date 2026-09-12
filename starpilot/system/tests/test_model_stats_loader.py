"""Exercise exact loader functions without starting modeld/hardware.
Synthetic pickle and OOB artifacts only, with the real chunked reader.
"""
import ast
import hashlib
import io
from pathlib import Path
import pickle
import shutil
import struct
import tempfile

from openpilot.common.file_chunker import open_file_chunked
from openpilot.starpilot.common.model_stats_identity import LoadedDigest, loaded_identity


def test_actual_loader_legacy_and_oob_loaded_identity(tmp_path):
  root = Path(__file__).resolve().parents[3]
  namespace = dict(Path=Path, pickle=pickle, io=io, struct=struct, shutil=shutil, tempfile=tempfile,
                   open_file_chunked=open_file_chunked, LoadedDigest=LoadedDigest, MAX_OOB_OPCODE_SIZE=1024**3)
  for file, names in [('selfdrive/modeld/helpers.py', {'dump_oob', 'load_oob'}),
                      ('selfdrive/modeld/modeld.py', {'_load_model_artifact', '_is_oob_artifact_header'})]:
    tree = ast.parse((root / file).read_text())
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(selected) == len(names)
    exec(compile(ast.Module(body=selected, type_ignores=[]), file, 'exec'), namespace)
  for oob in [False, True]:
    path = tmp_path / ('oob.pkl' if oob else 'legacy.pkl')
    with path.open('wb') as stream:
      if oob:
        namespace['dump_oob']({'weights': pickle.PickleBuffer(b'synthetic weights')}, stream)
      else:
        pickle.dump({'weights': b'synthetic weights'}, stream)
    identity = loaded_identity('actual-fallback', False)
    loaded = namespace['_load_model_artifact'](path, identity)
    assert bytes(loaded['weights']) == b'synthetic weights'
    assert identity['modelId'] == 'actual-fallback'
    assert identity['artifactVerified']
    assert identity['artifact'] == 'loaded-sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()
    assert bytes(namespace['_load_model_artifact'](path)['weights']) == b'synthetic weights'
