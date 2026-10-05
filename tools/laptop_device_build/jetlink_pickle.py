"""Inspect bare Jetlink captures with inert pickle globals; never run their code."""
import ast
import io
import pickle
from pathlib import Path
import re

GLOBALS = {
  'tinygrad.engine.jit._TinyJit', 'tinygrad.engine.jit.CapturedJit', 'tinygrad.tensor.Tensor',
  'tinygrad.uop.ops.UOp', 'tinygrad.uop.Ops', 'tinygrad.uop.ops.ParamArg', 'tinygrad.dtype.DType',
  'tinygrad.dtype.AddrSpace', 'tinygrad.device.Buffer', 'tinygrad.device.BufferSpec', 'builtins.bytearray',
  'tinygrad.uop.ops.CallInfo', 'tinygrad.uop.ops.AxisType', 'tinygrad.uop.ops.KernelInfo',
  'tinygrad.renderer.Estimates', 'tinygrad.uop.ops.ProgramInfo', 'tinygrad.helpers.Target',
  'tinygrad.runtime.support.hcq2.HCQInfo',
}


class Inert:
  def __new__(cls, *args):
    value = object.__new__(cls)
    value.args = args
    return value

  def __init__(self, *args):
    pass

  def __setstate__(self, state):
    self.state = state


class Inspector(pickle.Unpickler):
  def find_class(self, module, name):
    tag = f'{module}.{name}'
    if tag not in GLOBALS:
      raise ValueError(f'Unexpected Jetlink pickle global: {tag}')
    return type(name, (Inert,), {'tag': tag})

  def persistent_load(self, pid):
    raise ValueError('Persistent pickle references are not Jetlink captures')


def tagged(value, tag):
  return isinstance(value, Inert) and value.tag == tag


def walk(root):
  stack, seen = [root], set()
  while stack:
    value = stack.pop()
    if id(value) in seen:
      continue
    seen.add(id(value))
    if len(seen) > 200_000:
      raise ValueError('Jetlink capture exceeds inspection object bound')
    yield value
    if isinstance(value, Inert):
      stack.extend((value.args, getattr(value, 'state', None)))
    elif isinstance(value, (tuple, list)):
      stack.extend(value)
    elif isinstance(value, dict):
      stack.extend(value.values())


def op_codes():
  path = Path(__file__).resolve().parents[2] / 'tinygrad_repo/tinygrad/uop/__init__.py'
  body = next(node.body for node in ast.parse(path.read_text()).body if isinstance(node, ast.ClassDef) and node.name == 'Ops')
  names = [node.targets[0].id for node in body if isinstance(node, ast.Assign)]
  return {name: index + 1 for index, name in enumerate(names)}


def shape(view, codes):
  if not tagged(view, 'tinygrad.uop.ops.UOp') or len(view.args) != 5:
    raise ValueError('Missing Jetlink input/output shape UOp')
  op, sources = view.args[:2]
  if not tagged(op, 'tinygrad.uop.Ops') or op.args != (codes['RESHAPE'],):
    raise ValueError('Jetlink input/output is not explicitly shaped')
  dimensions = sources[1]
  if dimensions.args[0].args != (codes['STACK'],):
    raise ValueError('Missing Jetlink shape dimensions')
  values = []
  for dimension in dimensions.args[1]:
    if dimension.args[0].args != (codes['CONST'],) or type(dimension.args[2]) is not int:
      raise ValueError('Jetlink shape is not fixed')
    values.append(dimension.args[2])
  return tuple(values)


def dtype(value, name):
  return tagged(value, 'tinygrad.dtype.DType') and len(value.args) == 4 and value.args[2:] == name


def require_jetlink_qcom_pickle(path: Path) -> None:
  from openpilot.system.camerad.cameras.nv12_info import get_nv12_info
  match = re.fullmatch(r'jetlink_warp_(1344x760|1928x1208)_(512x256|1024x512)\.pkl', path.name)
  if not match:
    raise ValueError('Unsupported Jetlink warp geometry name')
  if not 0 < path.stat().st_size <= 100_000_000:
    raise ValueError('Jetlink pickle exceeds inspection byte bound')
  stream = io.BytesIO(path.read_bytes())
  try:
    root = Inspector(stream).load()
    if stream.read(1):
      raise ValueError('Trailing bytes after Jetlink capture')
    if not tagged(root, 'tinygrad.engine.jit._TinyJit') or len(root.args) != 2 or root.args[0] is not None:
      raise ValueError('Jetlink warp is not a bare captured TinyJit')
    capture = root.args[1]
    if not tagged(capture, 'tinygrad.engine.jit.CapturedJit') or len(capture.args) != 4:
      raise ValueError('Missing Jetlink CapturedJit')
    ret, linear, names, inputs = capture.args
    if names != ['big_frame', 'big_tfm', 'frame', 'tfm'] or len(inputs) != 4:
      raise ValueError('Jetlink warp input names/count differ')
    codes = op_codes()
    for index, (view, variables, kind, device) in enumerate(inputs):
      if variables or device != ('QCOM' if index in (0, 2) else 'NPY'):
        raise ValueError('Jetlink warp captured input backend differs')
      if not dtype(kind, ('unsigned char', 'B') if index in (0, 2) else ('float', 'f')):
        raise ValueError('Jetlink warp captured input dtype differs')
      if index in (1, 3) and shape(view, codes) != (3, 3):
        raise ValueError('Jetlink transform input shape differs')
    if not tagged(ret, 'tinygrad.tensor.Tensor') or not tagged(linear, 'tinygrad.uop.ops.UOp'):
      raise ValueError('Missing Jetlink tensor return or executable graph')
    mw, mh = map(int, match[2].split('x'))
    if shape(ret.state[1]['uop'], codes) != (2, 6, mh // 2, mw // 2):
      raise ValueError('Jetlink output shape differs')
    output = ret.state[1]['uop']
    for _ in range(100):
      parameter = output.args[2]
      if tagged(parameter, 'tinygrad.uop.ops.ParamArg'):
        state = parameter.state
        if state['device'] != 'QCOM' or state['size'] != 2 * 6 * (mh // 2) * (mw // 2) or not dtype(state['dtype'], ('unsigned char', 'B')):
          raise ValueError('Jetlink output buffer signature differs')
        break
      output = output.args[1][0]
    else:
      raise ValueError('Missing Jetlink output buffer')
    frame_size = get_nv12_info(*map(int, match[1].split('x')))[3]
    slots, compiled = set(), set()
    for node in walk(root):
      if tagged(node, 'tinygrad.uop.ops.UOp'):
        operation = node.args[0].args[0]
        if operation == codes['PROGRAM']:
          compiled.add('program')
        if operation == codes['BINARY'] and isinstance(node.args[2], bytes) and node.args[2]:
          compiled.add('binary')
      if isinstance(node, str) and (node.startswith(('METAL', 'AMD', 'USB+AMD'))):
        raise ValueError('Foreign Jetlink captured backend')
      if tagged(node, 'tinygrad.uop.ops.ParamArg'):
        state = node.state
        if state['device'] == 'QCOM' and state['slot'] in (0, 2):
          if state['size'] != frame_size or not dtype(state['dtype'], ('unsigned char', 'B')) or state['buffer'] is not None:
            raise ValueError('Jetlink frame input signature differs')
          slots.add(state['slot'])
    if slots != {0, 2}:
      raise ValueError('Missing paired QCOM frame inputs')
    if compiled != {'program', 'binary'}:
      raise ValueError('Missing compiled Jetlink execution graph')
  except (AttributeError, IndexError, KeyError, TypeError, pickle.UnpicklingError, EOFError) as error:
    raise ValueError('Malformed Jetlink capture') from error
