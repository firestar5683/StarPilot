import datetime
import hashlib
import http.server
import os
import struct
import threading
import zipfile
from pathlib import Path

import pytest

from openpilot.starpilot.system.android_auto import apk_identity, identity as identity_store

REAL_XAPK = Path(__file__).resolve().parents[4] / ".cache/android_auto/android-auto-17-6-663454-release.xapk"


def build_identity(days=365):
  from cryptography import x509
  from cryptography.hazmat.primitives import hashes, serialization
  from cryptography.hazmat.primitives.asymmetric import rsa
  from cryptography.x509.oid import NameOID

  now = datetime.datetime.now(datetime.UTC)

  def name(org):
    return x509.Name([x509.NameAttribute(NameOID.ORGANIZATION_NAME, org)])

  root_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
  root = (x509.CertificateBuilder().subject_name(name("Google Automotive Link")).issuer_name(name("Google Automotive Link"))
          .public_key(root_key.public_key()).serial_number(1).not_valid_before(now - datetime.timedelta(days=1))
          .not_valid_after(now + datetime.timedelta(days=3650)).add_extension(x509.BasicConstraints(ca=True, path_length=None), True)
          .sign(root_key, hashes.SHA256()))
  leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
  leaf = (x509.CertificateBuilder().subject_name(name("CarService")).issuer_name(root.subject).public_key(leaf_key.public_key())
          .serial_number(2).not_valid_before(now - datetime.timedelta(days=1)).not_valid_after(now + datetime.timedelta(days=days))
          .sign(root_key, hashes.SHA256()))
  pem = serialization.Encoding.PEM
  key_pem = leaf_key.private_bytes(pem, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
  root_sha = hashlib.sha256(root.public_bytes(serialization.Encoding.DER)).hexdigest()
  return leaf.public_bytes(pem), root.public_bytes(pem), key_pem, root_sha


def encrypt_key(cert, root, mask, key_pem):
  from cryptography.hazmat.primitives import padding
  from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
  material = apk_identity.derive_aes_material(cert, root, mask)
  padder = padding.PKCS7(128).padder()
  padded = padder.update(key_pem) + padder.finalize()
  encryptor = Cipher(algorithms.AES(material[:32]), modes.CBC(material[32:])).encryptor()
  return encryptor.update(padded) + encryptor.finalize()


def fill_array(data: bytes) -> bytes:
  return b"\x00\x03\x01\x00" + struct.pack("<I", len(data)) + data + (b"\x00" if len(data) % 2 else b"")


def fake_dex(*parts: bytes) -> bytes:
  out = bytearray(b"dex\n035\x00" + bytes(24))
  for part in parts:
    if len(out) % 2:
      out += b"\x00"
    out += part
  return bytes(out)


def string_item(text: bytes) -> bytes:
  return bytes([min(len(text), 127)]) + text + b"\x00"


@pytest.fixture(scope="module")
def ident():
  cert, root, key_pem, root_sha = build_identity()
  mask = bytes(range(256))
  blob = encrypt_key(cert, root, mask, key_pem)
  return {"cert": cert, "root": root, "key": key_pem, "root_sha": root_sha, "mask": mask, "blob": blob}


def make_apk(tmp_path, ident, *, name="app.apk", mask=None):
  mask = ident["mask"] if mask is None else mask
  decoy_mask = bytes(reversed(range(256)))
  dex1 = fake_dex(string_item(b"hello"), fill_array(decoy_mask), string_item(ident["cert"]), fill_array(bytes(1024)))
  dex2 = fake_dex(fill_array(mask), string_item(ident["root"]), fill_array(ident["blob"]))
  path = tmp_path / name
  with zipfile.ZipFile(path, "w") as apk:
    apk.writestr("AndroidManifest.xml", b"manifest")
    apk.writestr("classes.dex", dex1)
    apk.writestr("classes2.dex", dex2)
  return path


def make_xapk(tmp_path, ident):
  base = make_apk(tmp_path, ident, name="base-inner.apk").read_bytes()
  path = tmp_path / "app.xapk"
  with zipfile.ZipFile(path, "w") as xapk:
    xapk.writestr("config.arm64_v8a.apk", b"PK\x05\x06" + bytes(18))  # an empty split
    xapk.writestr("com.google.android.projection.gearhead.apk", base)
    xapk.writestr("manifest.json", b"{}")
  return path


def test_extracts_from_apk_and_xapk(tmp_path, ident):
  stages = []
  for path in (make_apk(tmp_path, ident), make_xapk(tmp_path, ident)):
    files, meta = apk_identity.extract_identity(path, root_sha256=ident["root_sha"], progress=stages.append)
    assert files["phone-cert.pem"] == ident["cert"] and files["root-cert.pem"] == ident["root"]
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    assert load_pem_private_key(files["phone-key.pem"], None).private_numbers() == load_pem_private_key(ident["key"], None).private_numbers()
    assert meta["key_matches"] and meta["root_sha256"] == ident["root_sha"]
  assert stages[:4] == ["reading", "searching", "decrypting", "verifying"]


def test_rejects_identity_not_from_google_root(tmp_path, ident):
  with pytest.raises(apk_identity.IdentityImportError, match="does not contain"):
    apk_identity.extract_identity(make_apk(tmp_path, ident))  # the real pinned root, not the fixture's


def test_rejects_when_no_mask_decrypts_the_key(tmp_path, ident):
  path = make_apk(tmp_path, ident, mask=bytes(256))
  with pytest.raises(apk_identity.IdentityImportError, match="stores its key differently"):
    apk_identity.extract_identity(path, root_sha256=ident["root_sha"])


def test_rejects_expired_certificate(tmp_path, ident):
  later = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=400)
  with pytest.raises(apk_identity.IdentityImportError, match="expired"):
    apk_identity.extract_identity(make_apk(tmp_path, ident), root_sha256=ident["root_sha"], now=later)


def test_rejects_non_apk_and_oversized_code(tmp_path, ident, monkeypatch):
  junk = tmp_path / "junk.apk"
  junk.write_bytes(b"not a zip")
  with pytest.raises(apk_identity.IdentityImportError, match="Not an APK"):
    apk_identity.extract_identity(junk)
  empty = tmp_path / "empty.apk"
  with zipfile.ZipFile(empty, "w") as z:
    z.writestr("readme.txt", "hi")
  with pytest.raises(apk_identity.IdentityImportError, match="No app code"):
    apk_identity.extract_identity(empty)
  monkeypatch.setattr(apk_identity, "MAX_DEX_BYTES", 64)
  with pytest.raises(apk_identity.IdentityImportError, match="too large"):
    apk_identity.extract_identity(make_apk(tmp_path, ident), root_sha256=ident["root_sha"])


def test_rejections_carry_codes_for_galaxy(tmp_path, ident):
  def code(path, **kwargs):
    with pytest.raises(apk_identity.IdentityImportError) as error:
      apk_identity.extract_identity(path, **kwargs)
    return error.value.code, error.value.expires

  junk = tmp_path / "junk.apk"
  junk.write_bytes(b"not a zip")
  assert code(junk) == ("NOT_PACKAGE", None)
  assert code(make_apk(tmp_path, ident)) == ("WRONG_APP", None)
  assert code(make_apk(tmp_path, ident, mask=bytes(256)), root_sha256=ident["root_sha"]) == ("UNSUPPORTED_VERSION", None)
  later = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=400)
  expired, expires = code(make_apk(tmp_path, ident), root_sha256=ident["root_sha"], now=later)
  assert expired == "EXPIRED" and datetime.datetime.fromisoformat(expires) < later

  job = apk_identity.ImportJob(work_dir=tmp_path / "work", identity_dir=tmp_path / "identity")
  job.start(path=junk)
  job.thread.join(30)
  assert job.status()["state"] == "failed" and job.status()["code"] == "NOT_PACKAGE"


def test_status_reports_date_of_expired_identity(tmp_path):
  cert, root, key_pem, _ = build_identity(days=0)
  directory = tmp_path / "identity"
  directory.mkdir()
  for name, content in {"phone-cert.pem": cert, "phone-key.pem": key_pem, "root-cert.pem": root}.items():
    (directory / name).write_bytes(content)
  os.chmod(directory / "phone-key.pem", 0o600)
  status = apk_identity.identity_status(directory)
  assert not status["installed"] and status["expired"] and status["expires"][:10] == datetime.datetime.now(datetime.UTC).date().isoformat()


def test_install_is_atomic_and_keeps_previous(tmp_path, ident):
  directory = tmp_path / "aa" / "identity"
  files = {"phone-cert.pem": ident["cert"], "phone-key.pem": ident["key"], "root-cert.pem": ident["root"]}
  apk_identity.install_identity(files, {"expires": "x"}, directory)
  assert apk_identity.identity_status(directory)["installed"]
  assert oct(os.stat(directory).st_mode & 0o777) == "0o700" and oct(os.stat(directory / "phone-key.pem").st_mode & 0o777) == "0o600"
  other_cert, other_root, _, _ = build_identity()
  with pytest.raises(identity_store.IdentityError):  # key does not match the certificate: nothing changes
    apk_identity.install_identity({**files, "phone-cert.pem": other_cert, "root-cert.pem": other_root}, {}, directory)
  assert (directory / "phone-cert.pem").read_bytes() == ident["cert"]
  assert not [p for p in directory.parent.iterdir() if p.name.startswith(".identity-")]
  apk_identity.install_identity(files, {"expires": "y"}, directory)
  assert (directory.parent / "identity.previous" / "phone-cert.pem").exists()
  apk_identity.remove_identity(directory)
  assert apk_identity.identity_status(directory) == {"installed": False, "message": "No Android Auto identity installed"}


def test_import_stops_when_master_switch_is_disabled(monkeypatch, tmp_path):
  source = tmp_path / "upload.apk"
  source.write_bytes(b"test")
  enabled = {"value": True}

  def extract(*args, progress, **kwargs):
    enabled["value"] = False
    progress("reading")
    raise AssertionError("disabled import continued")

  monkeypatch.setattr(apk_identity, "extract_identity", extract)
  def unexpected_install(*args):
    raise AssertionError("disabled import installed a certificate")
  monkeypatch.setattr(apk_identity, "install_identity", unexpected_install)
  job = apk_identity.ImportJob(work_dir=tmp_path)
  job.start(path=source, enabled=lambda: enabled["value"])
  job.thread.join(timeout=5)
  assert not job.busy()
  assert "disabled" in job.status()["error"]
  assert not source.exists()


def test_status_reports_expiry(tmp_path):
  cert, root, key_pem, _ = build_identity(days=5)
  directory = tmp_path / "identity"
  apk_identity.install_identity({"phone-cert.pem": cert, "phone-key.pem": key_pem, "root-cert.pem": root}, {"subject": "O=CarService"}, directory)
  status = apk_identity.identity_status(directory)
  assert status["installed"] and status["days_left"] in (4, 5) and "renew" in status["warning"]


def test_certificate_days_left_reads_only_the_certificate(tmp_path):
  cert, _, _, _ = build_identity(days=5)
  directory = tmp_path / "identity"
  directory.mkdir()
  assert identity_store.certificate_days_left(directory) is None
  (directory / identity_store.CERT_NAME).write_bytes(cert)  # no key: the car view never reads it
  assert identity_store.certificate_days_left(directory) in (4, 5)
  (directory / identity_store.CERT_NAME).write_bytes(b"not a certificate")
  assert identity_store.certificate_days_left(directory) is None


def wait_job(job):
  job.thread.join(30)
  return job.status()


def test_import_job_from_upload_and_from_link(tmp_path, ident):
  directory = tmp_path / "aa" / "identity"
  job = apk_identity.ImportJob(work_dir=tmp_path / "work", identity_dir=directory, root_sha256=ident["root_sha"])
  job.upload_path().write_bytes(make_xapk(tmp_path, ident).read_bytes())
  job.start()
  status = wait_job(job)
  assert status["state"] == "done", status
  assert apk_identity.identity_status(directory)["installed"] and not job.upload_path().exists()

  served = make_apk(tmp_path, ident).read_bytes()

  class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
      self.send_response(200)
      self.send_header("Content-Length", str(len(served)))
      self.end_headers()
      self.wfile.write(served)

    def log_message(self, *args, **kwargs):
      pass

  server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
  threading.Thread(target=server.serve_forever, daemon=True).start()
  try:
    job.start(url=f"http://127.0.0.1:{server.server_port}/aa.apk")
    status = wait_job(job)
    assert status["state"] == "done" and status["downloaded"] == len(served), status
  finally:
    server.shutdown()
  job.start(url="ftp://example.com/aa.apk")
  status = wait_job(job)
  assert status["state"] == "failed" and "http(s)" in status["error"]


@pytest.mark.skipif(not REAL_XAPK.exists(), reason="the user's own Android Auto XAPK is not in .cache/")
def test_real_android_auto_17_6_xapk():
  files, meta = apk_identity.extract_identity(REAL_XAPK)
  assert meta["root_sha256"] == apk_identity.GOOGLE_ROOT_SHA256 and "CarService" in meta["subject"]
  assert set(files) == {"phone-cert.pem", "phone-key.pem", "root-cert.pem"}
