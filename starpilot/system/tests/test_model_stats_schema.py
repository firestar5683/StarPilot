"""Schema serialization only; not a native target build."""
from pathlib import Path
import capnp


def test_runtime_provenance_schema_roundtrip():
  schema = capnp.load(str(Path(__file__).resolve().parents[3] / 'cereal/custom.capnp'))
  message = schema.StarPilotModelDataV2.new_message(runtimeIdentity='synthetic identity', modelMonoTime=123,
                                                   turnDirection='none')
  with schema.StarPilotModelDataV2.from_bytes(message.to_bytes()) as result:
    assert result.runtimeIdentity == 'synthetic identity'
    assert result.modelMonoTime == 123
    assert str(result.turnDirection) == 'none'
