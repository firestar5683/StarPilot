"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

A driving model's graph metadata: input and output names and shapes, plus
openpilot's output_slices and model_checkpoint metadata_props.

Adapter over whichever parser the host has, neither a hard dependency.
tinygrad's OnnxPBParser is preferred and is what openpilot's
get_model_metadata.py uses: it walks the protobuf without materialising 766 MB
of weights, and a comma has it already. The onnx package is the fallback
everywhere else.
"""
from __future__ import annotations

import codecs
import pickle
from dataclasses import dataclass, field


@dataclass
class OnnxMeta:
  inputs: dict[str, tuple[int, ...]] = field(default_factory=dict)
  outputs: dict[str, tuple[int, ...]] = field(default_factory=dict)
  props: dict[str, str] = field(default_factory=dict)

  @property
  def output_slices(self) -> dict[str, slice]:
    """openpilot stashes a base64 pickle of the output slice map in metadata_props."""
    raw = self.props.get('output_slices')
    if raw is None:
      raise KeyError("output_slices not in model metadata_props")
    return pickle.loads(codecs.decode(raw.encode(), 'base64'))

  @property
  def model_checkpoint(self) -> str | None:
    return self.props.get('model_checkpoint')


def _parse_tinygrad(path: str) -> OnnxMeta:
  """Same approach as openpilot's get_model_metadata.py, without importing it.

  ModelProto is narrowed to two fields, so the 766 MB of initializers are
  skipped rather than built.
  """
  from tinygrad.nn.onnx import OnnxPBParser

  class _MetaParser(OnnxPBParser):
    def _parse_ModelProto(self) -> dict:
      obj: dict = {"graph": {"input": [], "output": []}, "metadata_props": []}
      for fid, wire_type in self._parse_message(self.reader.len):
        if fid == 7:
          obj["graph"] = self._parse_GraphProto()
        elif fid == 14:
          obj["metadata_props"].append(self._parse_StringStringEntryProto())
        else:
          self.reader.skip_field(wire_type)
      return obj

  model = _MetaParser(path).parse()
  meta = OnnxMeta()
  for key, dest in (('input', meta.inputs), ('output', meta.outputs)):
    for vi in model['graph'][key]:
      dest[vi['name']] = tuple(int(d) if isinstance(d, int) else 0 for d in vi['parsed_type'].shape)
  for prop in model['metadata_props']:
    meta.props[prop['key']] = prop['value']
  return meta


def _parse_onnx(path: str) -> OnnxMeta:
  import onnx

  model = onnx.load(path, load_external_data=False)
  meta = OnnxMeta()
  for vis, dest in ((model.graph.input, meta.inputs), (model.graph.output, meta.outputs)):
    for vi in vis:
      dest[vi.name] = tuple(d.dim_value for d in vi.type.tensor_type.shape.dim)
  for p in model.metadata_props:
    meta.props[p.key] = p.value
  return meta


def parse_file(path: str) -> OnnxMeta:
  errors = []
  for name, fn in (('tinygrad', _parse_tinygrad), ('onnx', _parse_onnx)):
    try:
      return fn(path)
    except Exception as e:
      # not just ImportError: a parser that chokes on a newer layout falls
      # through to the other one rather than aborting
      errors.append(f'{name}: {type(e).__name__}: {e}')
  raise RuntimeError(
    "could not read model metadata; need tinygrad or the onnx package. Tried:\n  "
    + "\n  ".join(errors))

