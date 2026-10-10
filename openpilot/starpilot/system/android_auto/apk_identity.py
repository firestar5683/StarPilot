"""Extract and install the Android Auto phone identity from the user's own copy of the app.

The car accepts a projection source only when it presents Google's Android Auto
phone certificate and proves it holds the matching key. Both are embedded in the
Android Auto app, so each user supplies their own APK (or XAPK/APKM bundle) and
the comma extracts the identity on device. Packages can also be fetched directly
from Google Play using the user's own account; no project broker is involved.

Extraction needs no decompiler. The app's DEX files hold the phone certificate
and the Google Automotive Link root as PEM string constants, and the key as an
AES-encrypted static byte array next to a 256-byte mask (``fill-array-data``
payloads). Every certificate and candidate array is found by content, so the
obfuscated class names do not matter, and each mask/ciphertext pair is tried.

The extracted identity is accepted only when the key matches the phone
certificate, the certificate is issued by Google's root (pinned fingerprint),
and both certificates are currently valid. These checks validate the extracted
identity; they do not verify the APK's signing certificate or other contents.

The key derivation follows https://github.com/tomasz-grobelny/AACS/issues/15, as
first implemented in yummydirtx/openpilot ``tools/android_auto/import_identity.py``
(MIT, pinned at 672a16f6183567c0ada53654f8527d97e1a483fa). No APK, certificate or
key is distributed with this code.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import struct
import tempfile
import threading
import urllib.request
import zipfile
import zlib
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from openpilot.starpilot.system.android_auto import identity as identity_store
from openpilot.starpilot.system.android_auto import play_resolver

# SHA-256 of the DER Google Automotive Link root certificate (valid until 2044).
GOOGLE_ROOT_SHA256 = "49e52efc13ad2ed09f204c3b10698bd84bb7105f510558aa14b8119a5c4ad17f"
PACKAGE = "com.google.android.projection.gearhead"
KNOWN_GOOD_VERSION = "17.6.663454-release"

MAX_FILE_BYTES = 256 * 1024 * 1024       # an uploaded or downloaded APK/XAPK/APKM
MAX_APK_BYTES = 192 * 1024 * 1024        # the base APK inside a bundle
MAX_DEX_BYTES = 64 * 1024 * 1024         # one classes*.dex
MAX_DEX_FILES = 32
MAX_CANDIDATES = 64
MASK_SIZE = 256
PEM = re.compile(rb"-----BEGIN CERTIFICATE-----[\s\S]{100,8000}?-----END CERTIFICATE-----\n\x00")
FILL_ARRAY_BYTES = re.compile(rb"\x00\x03\x01\x00")  # fill-array-data payload header, element width 1
DEX_NAME = re.compile(r"classes\d*\.dex")
IMPORT_DIR = identity_store.DATA_DIR / "import"


class IdentityImportError(RuntimeError):
  """A rejected package. ``code`` lets Galaxy explain the problem without parsing the message."""

  def __init__(self, message: str, code: str = "FAILED", expires: str | None = None):
    super().__init__(message)
    self.code = code
    self.expires = expires


# ------------------------------------------------------------------ extraction

def derive_aes_material(cert: bytes, root: bytes, mask: bytes) -> bytes:
  """Key and IV derivation used by the Android Auto app to protect its embedded key."""
  state = bytearray(48)

  def mix(data):
    for pos in range(len(data)):
      for i in range(48):
        b = state[i]
        # data may alias state in later rounds, so read data[pos] inside the loop
        state[i] = ((((b >> 7) | (b + b)) + 33) ^ mask[i % len(mask)] ^ data[pos]) & 255

  mix(cert)
  mix(root)
  for _ in range(7):
    mix(state)
  return bytes(state)


def _checked_read(archive: zipfile.ZipFile, info: zipfile.ZipInfo, limit: int) -> bytes:
  if info.file_size > limit:
    raise IdentityImportError(f"{info.filename} is too large ({info.file_size // (1024 * 1024)} MB)", "TOO_LARGE")
  with archive.open(info) as handle:
    data = handle.read(limit + 1)
  if len(data) > limit:
    raise IdentityImportError(f"{info.filename} is larger than it claims", "CORRUPT")
  return data


def _dex_files(path: Path) -> tuple[list[bytes], str]:
  """The DEX files of the Android Auto app in an APK, XAPK or APKM; returns (dexes, description)."""
  if path.stat().st_size > MAX_FILE_BYTES:
    raise IdentityImportError("File is too large to be the Android Auto app", "TOO_LARGE")
  try:
    outer = zipfile.ZipFile(path)
  except zipfile.BadZipFile as error:
    raise IdentityImportError("Not an APK, XAPK or APKM file", "NOT_PACKAGE") from error
  with outer:
    names = [info for info in outer.infolist() if DEX_NAME.fullmatch(info.filename)]
    if names:
      return [_checked_read(outer, info, MAX_DEX_BYTES) for info in names[:MAX_DEX_FILES]], "apk"
    # A bundle: the base APK is the inner APK that contains code.
    for info in sorted((i for i in outer.infolist() if i.filename.endswith(".apk")),
                       key=lambda i: (PACKAGE not in i.filename and "base" not in i.filename, -i.file_size)):
      inner_bytes = _checked_read(outer, info, MAX_APK_BYTES)
      try:
        inner = zipfile.ZipFile(io.BytesIO(inner_bytes))
      except zipfile.BadZipFile:
        continue
      with inner:
        dex = [i for i in inner.infolist() if DEX_NAME.fullmatch(i.filename)]
        if dex:
          return [_checked_read(inner, i, MAX_DEX_BYTES) for i in dex[:MAX_DEX_FILES]], f"bundle ({info.filename})"
  raise IdentityImportError("No app code found; choose the Android Auto APK, XAPK, or APKM", "NO_CODE")


def _candidates(dexes: list[bytes]) -> tuple[set[bytes], list[bytes], list[bytes]]:
  pems: set[bytes] = set()
  masks: list[bytes] = []
  blobs: list[bytes] = []
  for dex in dexes:
    pems.update(match.group()[:-1] for match in PEM.finditer(dex))
    for match in FILL_ARRAY_BYTES.finditer(dex):
      if match.start() % 2 or match.end() + 4 > len(dex):
        continue  # payloads are 16-bit aligned
      size = struct.unpack_from("<I", dex, match.end())[0]
      start = match.end() + 4
      if start + size > len(dex):
        continue
      if size == MASK_SIZE and len(masks) < MAX_CANDIDATES:
        masks.append(dex[start:start + size])
      elif 512 <= size <= 8192 and size % 16 == 0 and len(blobs) < MAX_CANDIDATES:
        blobs.append(dex[start:start + size])
  return pems, masks, blobs


def _not_after(cert):
  return cert.not_valid_after_utc if hasattr(cert, "not_valid_after_utc") else cert.not_valid_after.replace(tzinfo=UTC)


def _not_before(cert):
  return cert.not_valid_before_utc if hasattr(cert, "not_valid_before_utc") else cert.not_valid_before.replace(tzinfo=UTC)


def extract_identity(path: Path, *, root_sha256: str = GOOGLE_ROOT_SHA256, now: datetime | None = None,
                     progress: Callable[[str], None] = lambda stage: None) -> tuple[dict[str, bytes], dict]:
  """Return ({file name: PEM bytes}, metadata) for the identity in an Android Auto APK/XAPK/APKM."""
  from cryptography import x509
  from cryptography.hazmat.primitives import padding, serialization
  from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

  progress("reading")
  dexes, source = _dex_files(Path(path))
  progress("searching")
  pems, masks, blobs = _candidates(dexes)
  del dexes
  certs = {}
  for pem in pems:
    try:
      certs[pem] = x509.load_pem_x509_certificate(pem)
    except ValueError:
      continue
  der_sha = {pem: hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest() for pem, cert in certs.items()}
  roots = [pem for pem in certs if der_sha[pem] == root_sha256]
  if not roots:
    raise IdentityImportError("This file does not contain the Android Auto identity; choose the Android Auto app itself", "WRONG_APP")
  root_pem = roots[0]
  root = certs[root_pem]
  leaves = []
  for pem, cert in certs.items():
    if pem == root_pem:
      continue
    try:
      cert.verify_directly_issued_by(root)
      leaves.append(pem)
    except Exception:
      continue
  if not leaves:
    raise IdentityImportError("No phone certificate issued by Google's Automotive Link root was found", "UNVERIFIED")

  progress("decrypting")
  for leaf_pem in leaves:
    leaf = certs[leaf_pem]
    wanted = leaf.public_key().public_numbers()
    for mask in masks:
      material = derive_aes_material(leaf_pem, root_pem, mask)
      for blob in blobs:
        try:
          decryptor = Cipher(algorithms.AES(material[:32]), modes.CBC(material[32:])).decryptor()
          unpadder = padding.PKCS7(128).unpadder()
          plain = unpadder.update(decryptor.update(blob) + decryptor.finalize()) + unpadder.finalize()
          key = serialization.load_pem_private_key(plain, password=None)
        except Exception:
          continue
        if key.public_key().public_numbers() != wanted:
          continue
        progress("verifying")
        now = now or datetime.now(UTC)
        for name, cert in (("phone certificate", leaf), ("Google root", root)):
          if now < _not_before(cert):
            raise IdentityImportError(f"The {name} in this app is not valid yet; check the comma's clock", "NOT_YET_VALID")
          if now >= _not_after(cert):
            raise IdentityImportError(f"The {name} in this app expired on {_not_after(cert).date()}; use a newer Android Auto version",
                                      "EXPIRED", _not_after(cert).isoformat())
        pem_key = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        metadata = {
          "subject": leaf.subject.rfc4514_string(),
          "expires": _not_after(leaf).isoformat(),
          "certificate_sha256": der_sha[leaf_pem],
          "root_sha256": der_sha[root_pem],
          "source": source,
          "imported": datetime.now(UTC).isoformat(timespec="seconds"),
          "key_matches": True,
        }
        return {identity_store.CERT_NAME: leaf_pem, identity_store.KEY_NAME: pem_key, identity_store.ROOT_NAME: root_pem}, metadata
  raise IdentityImportError(f"This Android Auto version stores its key differently; use version {KNOWN_GOOD_VERSION} or another that works",
                           "UNSUPPORTED_VERSION")


# ------------------------------------------------------------------ install

def install_identity(files: dict[str, bytes], metadata: dict, directory: Path | None = None) -> None:
  """Atomically replace the identity directory, keeping the previous one as ``identity.previous``."""
  directory = directory or identity_store.IDENTITY_DIR
  directory.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
  staging = Path(tempfile.mkdtemp(prefix=".identity-", dir=directory.parent))
  try:
    os.chmod(staging, 0o700)
    for name, content in {**files, "provenance.json": (json.dumps(metadata, indent=2) + "\n").encode()}.items():
      with os.fdopen(os.open(staging / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    identity_store.load_identity(staging)  # the service must be able to use it before it goes live
    previous = directory.with_name(directory.name + ".previous")
    if directory.exists():
      shutil.rmtree(previous, ignore_errors=True)
      os.replace(directory, previous)
    os.replace(staging, directory)
  except BaseException:
    shutil.rmtree(staging, ignore_errors=True)
    raise


def remove_identity(directory: Path | None = None) -> None:
  directory = directory or identity_store.IDENTITY_DIR
  shutil.rmtree(directory, ignore_errors=True)


def identity_status(directory: Path | None = None) -> dict:
  directory = directory or identity_store.IDENTITY_DIR
  if not (directory / identity_store.CERT_NAME).exists():
    return {"installed": False, "message": "No Android Auto identity installed"}
  try:
    ident = identity_store.load_identity(directory)
  except identity_store.IdentityError as error:
    status = {"installed": False, "expired": "expired" in str(error), "error": str(error), "message": str(error)}
    try:
      expires = identity_store._not_after(directory / identity_store.CERT_NAME)
    except (OSError, ValueError):
      expires = None
    if expires is not None:
      status["expires"] = expires.isoformat()
    return status
  try:
    provenance = json.loads((directory / "provenance.json").read_text())
  except (OSError, ValueError):
    provenance = {}
  return {
    "installed": True,
    "expires": ident.expires,
    "days_left": ident.days_left,
    "warning": identity_store.expiry_warning(ident),
    "subject": provenance.get("subject", ""),
    "certificate_sha256": provenance.get("certificate_sha256", ""),
    "imported": provenance.get("imported", ""),
    "source": provenance.get("source", ""),
  }


# ------------------------------------------------------------------ background import

def download(url: str, destination: Path, progress: Callable[[int, int], None] = lambda done, total: None,
             *, google_play: bool = False) -> None:
  if not url.lower().startswith(("https://", "http://")):
    raise IdentityImportError("Enter an http(s) link to the APK, XAPK, or APKM", "DOWNLOAD")
  request = urllib.request.Request(url, headers={"User-Agent": "StarPilot-AndroidAuto/1"})
  try:
    opener = urllib.request.build_opener(play_resolver.GoogleRedirect(), urllib.request.ProxyHandler({})) if google_play else None
    if google_play:
      play_resolver.validate_url(url)
    open_url = opener.open if opener else urllib.request.urlopen
    with open_url(request, timeout=30) as response, open(destination, "wb") as handle:
      total = int(response.headers.get("Content-Length") or 0)
      if total > MAX_FILE_BYTES:
        raise IdentityImportError("That file is too large to be the Android Auto app", "TOO_LARGE")
      done = 0
      while chunk := response.read(1024 * 1024):
        done += len(chunk)
        if done > MAX_FILE_BYTES:
          raise IdentityImportError("That file is too large to be the Android Auto app", "TOO_LARGE")
        handle.write(chunk)
        progress(done, total)
  except IdentityImportError:
    raise
  except Exception as error:
    raise IdentityImportError(f"Download failed: {error}", "DOWNLOAD") from error


class ImportJob:
  """One identity import at a time, in a background thread, with pollable status."""

  def __init__(self, work_dir: Path | None = None, identity_dir: Path | None = None, root_sha256: str = GOOGLE_ROOT_SHA256,
               token_store: play_resolver.TokenStore | None = None):
    self.token_store = token_store or play_resolver.TokenStore()
    self.work_dir = work_dir or IMPORT_DIR
    self.identity_dir = identity_dir
    self.root_sha256 = root_sha256
    self.lock = threading.Lock()
    self.thread: threading.Thread | None = None
    self.state: dict = {"state": "idle"}

  def status(self) -> dict:
    with self.lock:
      return dict(self.state)

  def _set(self, **values) -> None:
    with self.lock:
      self.state.update(values)

  def busy(self) -> bool:
    return self.thread is not None and self.thread.is_alive()

  def upload_path(self) -> Path:
    self.work_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    return self.work_dir / "android-auto-upload.bin"

  def start(self, *, path: Path | None = None, url: str = "", enabled=None) -> None:
    with self.lock:  # check and claim together, so two requests cannot both start
      if self.busy():
        raise IdentityImportError("An import is already running")
      self.state = {"state": "running", "stage": "downloading" if url else "reading", "started": datetime.now(UTC).timestamp(),
                    "downloaded": 0, "total": 0}
      self.thread = threading.Thread(target=self._run, args=(path, url, enabled), name="android_auto_identity_import", daemon=True)
      self.thread.start()

  def start_google_import(self, *, email: str, oauth_token: str | None = None, aas_token: str | None = None,
                          save_token: bool = False, enabled=None) -> None:
    if bool(oauth_token) == bool(aas_token) or type(save_token) is not bool:
      raise play_resolver.PlayError("Supply one Google sign-in token")
    token = oauth_token or aas_token
    play_resolver.validate_credentials(email, token)
    with self.lock:
      if self.busy():
        raise IdentityImportError("An import is already running")
      self.state = {"state": "running", "stage": "authenticating", "source": "google",
                    "started": datetime.now(UTC).timestamp(), "downloaded": 0, "total": 0}
      self.thread = threading.Thread(target=self._run_google, args=(email, token, save_token, enabled),
                                     name="android_auto_google_import", daemon=True)
      self.thread.start()

  def _run_google(self, email: str, token: str, remember: bool, enabled) -> None:
    source = None
    result = None

    def progress(stage=None, **values):
      if enabled is not None and not enabled():
        raise IdentityImportError("Import cancelled: authorization changed", "CANCELLED")
      self._set(**({"stage": stage} if stage else {}), **values)

    try:
      progress("authenticating")
      self.work_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
      fd, name = tempfile.mkstemp(prefix="google-import-", suffix=".apk", dir=self.work_dir)
      os.close(fd)
      source = Path(name)
      result = play_resolver.resolve(email, token, remember=remember, progress=progress)
      token = ""
      progress("downloading")
      download(result['url'], source, lambda done, total: progress(downloaded=done, total=total), google_play=True)
      result.pop('url', None)
      progress("installing")
      files, metadata = extract_identity(source, root_sha256=self.root_sha256, progress=lambda _stage: progress())
      metadata['source'] = 'Google Play (user account)'
      progress()
      install_identity(files, metadata, self.identity_dir)
      progress()
      if remember:
        self.token_store.save(email, result['aas_token'])
      else:
        self.token_store.forget()
      self._set(state="done", stage="done", finished=datetime.now(UTC).timestamp(), expires=metadata['expires'],
                message=f"Identity installed; valid until {metadata['expires'][:10]}")
    except IdentityImportError as error:
      # Download exceptions may contain signed URLs. Only extraction errors are
      # safe to display; never pass through network or unexpected error text.
      message = 'Google Play download failed; try again' if error.code == 'DOWNLOAD' else str(error)
      self._set(state="failed", error=message, code=error.code, finished=datetime.now(UTC).timestamp(),
                **({"expires": error.expires} if error.expires else {}))
    except play_resolver.PlayError as error:
      self._set(state="failed", error=str(error), code="GOOGLE_PLAY", finished=datetime.now(UTC).timestamp())
    except Exception:
      self._set(state="failed", error="Google Play import failed; try again or use manual upload",
                code="GOOGLE_PLAY", finished=datetime.now(UTC).timestamp())
    finally:
      token = ""
      if result is not None:
        result.clear()
      if source is not None:
        try:
          source.unlink(missing_ok=True)
        except OSError:
          pass

  def _run(self, path: Path | None, url: str, enabled=None) -> None:
    def progress(**values):
      if enabled is not None and not enabled():
        raise IdentityImportError("Import cancelled: Android Auto is disabled", "CANCELLED")
      self._set(**values)

    source = path or self.upload_path()
    try:
      progress()
      if url:
        download(url, source, lambda done, total: progress(downloaded=done, total=total))
      files, metadata = extract_identity(source, root_sha256=self.root_sha256, progress=lambda stage: progress(stage=stage))
      progress(stage="installing")
      install_identity(files, metadata, self.identity_dir)
      self._set(state="done", stage="done", finished=datetime.now(UTC).timestamp(), expires=metadata["expires"],
                message=f"Identity installed; valid until {metadata['expires'][:10]}")
    except IdentityImportError as error:
      self._set(state="failed", finished=datetime.now(UTC).timestamp(), error=str(error), code=error.code,
                **({"expires": error.expires} if error.expires else {}))
    except (zipfile.BadZipFile, EOFError, zlib.error) as error:  # a truncated or damaged download
      self._set(state="failed", finished=datetime.now(UTC).timestamp(), error=f"The package is damaged: {error}", code="CORRUPT")
    except Exception as error:
      self._set(state="failed", finished=datetime.now(UTC).timestamp(), error=f"{type(error).__name__}: {error}", code="FAILED")
    finally:
      try:
        source.unlink(missing_ok=True)
      except OSError:
        pass
