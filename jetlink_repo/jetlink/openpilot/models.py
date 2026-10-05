"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

Which large model runs, and where its bytes are.

The large model is the model manager's big-model pick, the same slot a
chestnut runs from (Keys.big_model). Its bundles are tinygrad pkls for a GPU
the Jetson does not have, but each one names the comma commit it was compiled
from, and that commit's ONNX in comma's LFS is what the Jetson runs. The
catalog says what exists, the slot says which one, the pointer at the commit
says which bytes. A commit that ships a precompiled pkl instead names its
export, and jetlink's registry follows that to comma's model repo; see
jetlink.registry.lfs.

Without a model manager (Keys.big_model and Keys.catalog None) there is no
pick and no catalog, and the large model is jetlink's own default, named by its
ref: its pointer resolves from the ref as any pick's does.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from jetlink.registry.catalog import DEFAULT_BIG_MODEL_NAME, DEFAULT_BIG_MODEL_REF

POINTER_TIMEOUT = 10.0
_REF = re.compile(r'[0-9a-f]{40}')
# the build date a catalog name ends in, " (September 17, 2026)"; any other parenthesis stays
_TRAILING_DATE = re.compile(r' \([A-Za-z]+ \d{1,2}, \d{4}\)$')
# the index and the slot are JSON params, and the UI names the active model
# every frame; the status line can lag a new pick by this long
INDEX_TTL = 2.0


class Models:
  def __init__(self, op):
    self.op = op
    self._index_cache: tuple[float, list[dict], dict[str, dict]] | None = None
    self._slot_cache: tuple[float, dict | None] | None = None

  def catalog(self) -> list[dict]:
    """sunnypilot's big-model bundles as {name, ref}, newest first, as the model
    manager's own picker lists them. From the cached JSON rather than the parsed
    bundles: parsing builds capnp objects and writes chunk manifests, for two
    fields. Never raises."""
    try:
      key = self.op.keys.catalog
      bundles = ((self.op.get(key) if key else None) or {}).get('bundles', [])
      found = [b for b in bundles if _REF.fullmatch(str(b.get('ref')))
               and int(b.get('minimum_selector_version', 0)) == self.op.catalog_selector]
    except Exception:
      self.op.log.exception("jetlink: could not read the big-model catalog")
      return []
    found.sort(key=lambda b: int(b.get('index', 0)), reverse=True)
    return [{'name': str(b.get('display_name') or b['ref'][:10]), 'ref': b['ref']} for b in found]

  def pointers(self) -> dict[str, dict]:
    value = self.op.get(self.op.keys.pointers)
    return value if isinstance(value, dict) else {}

  def fetch_pointer(self, ref: str) -> tuple[str, int]:
    """The oid and size of the ONNX a comma commit names, in its tree or, for a
    precompiled-pkl commit, in comma's model repo. The Jetson's registry does
    the same lookup, so the two ends agree on every model's identity."""
    from jetlink.registry.lfs import fetch_pointer as registry_fetch_pointer
    pointer = registry_fetch_pointer(ref, timeout=POINTER_TIMEOUT)
    return pointer.oid, pointer.size

  def resolve_pointer(self, ref: str) -> tuple[str, int]:
    """The oid and size behind a catalog model, fetched the first time and kept for good."""
    known = self.pointers()
    if ref in known:
      return known[ref]['oid'], int(known[ref]['size'])
    oid, size = self.fetch_pointer(ref)
    known[ref] = {'oid': oid, 'size': size}
    # blocking: the next lookup reads this back, and a put still in flight would be lost under it
    self.op.put(self.op.keys.pointers, known, block=True)
    self._index_cache = None
    self.op.log.warning("jetlink: %s is %s, %d MB", ref[:10], oid[:16], size >> 20)
    return oid, size

  @staticmethod
  def _row(name: str, ref: str, known: dict[str, dict]) -> dict:
    p = known.get(ref) or {}
    return {'name': name, 'ref': ref, 'oid': p.get('oid'), 'size': int(p['size']) if p.get('size') else None}

  def _index(self) -> tuple[list[dict], dict[str, dict]]:
    """The catalog's rows and the pointers behind them, read together once per INDEX_TTL."""
    now = time.monotonic()
    if self._index_cache is None or now - self._index_cache[0] >= INDEX_TTL:
      known = self.pointers()
      self._index_cache = (now, [self._row(b['name'], b['ref'], known) for b in self.catalog()], known)
    return self._index_cache[1], self._index_cache[2]

  def model_index(self) -> list[dict]:
    """Every catalog model, {name, ref, oid, size}. oid and size are None until
    the model has been selected and resolved. No network."""
    return self._index()[0]

  def selected_slot(self) -> dict | None:
    """The big-model slot's pick as {name, ref}, from the raw param rather than a
    parsed bundle, and memoised: the UI asks every frame."""
    now = time.monotonic()
    if self._slot_cache is not None and now - self._slot_cache[0] < INDEX_TTL:
      return self._slot_cache[1]
    key = self.op.keys.big_model
    slot = self.op.get(key) if key else None
    ref = slot.get('ref') if isinstance(slot, dict) else None
    pick = None
    if isinstance(ref, str) and ref:
      pick = {'name': str(slot.get('displayName') or ref[:10]), 'ref': ref}
    self._slot_cache = (now, pick)
    return pick

  def default_model(self) -> dict | None:
    """What runs with no pick: jetlink's default big model, else the newest the
    catalog lists. Not the chestnut's default, which is the model in the tree.
    A fork with no catalog at all (Keys.catalog None) gets jetlink's default by
    its ref; one whose catalog has not been fetched yet waits for it, as ever."""
    if self.op.keys.catalog is None:
      return self._row(DEFAULT_BIG_MODEL_NAME, DEFAULT_BIG_MODEL_REF, self._index()[1])
    models = self.model_index()
    return next((m for m in models if m['ref'] == DEFAULT_BIG_MODEL_REF), models[0] if models else None)

  def default_model_name(self) -> str | None:
    """default_model()'s name without the catalog's trailing build date, the
    form the chestnut's DEFAULT_BIG_MODEL has. Per frame from the UI, off the
    index's cache."""
    model = self.default_model()
    return _TRAILING_DATE.sub('', model['name']) if model else None

  def selected_model(self) -> dict | None:
    """The slot's pick, listed in the catalog or not: a ref is enough to find its
    pointer. With no pick, default_model()."""
    if (pick := self.selected_slot()) is not None:
      return self._row(pick['name'], pick['ref'], self._index()[1])
    return self.default_model()

  def selected_model_name(self) -> str | None:
    selected = self.selected_model()
    return selected['name'] if selected else None

  def model_dir(self) -> Path:
    """Ours, under the model manager's root: its cache clear removes every file
    it does not recognise and leaves directories alone."""
    return Path(self.op.model_root()) / 'jetlink'

  @staticmethod
  def model_file_name(model: dict) -> str:
    """One file per model, so switching back does not re-download."""
    return f"{model['oid'][:16]}.onnx"

  def shipped_model_path(self) -> Path | None:
    """The chosen large model, if it has been fetched. Keyed on the oid, not
    the in-tree pointer, which moves with upstream syncs; the size is the cheap
    check that the file is the one we mean."""
    model = self.selected_model()
    if model is None or not model['oid']:
      return None
    path = self.model_dir() / self.model_file_name(model)
    if path.is_file() and path.stat().st_size == model['size']:
      return path
    return None

  def lfs_endpoints(self) -> list[str]:
    """Where a model's bytes are asked for, nearest first: the LFS server this
    checkout's .lfsconfig names (a release ships none), then the ones the Jetson
    asks."""
    from jetlink.registry.lfs import LFS_ENDPOINTS
    out = []
    try:
      for line in (Path(self.op.basedir) / '.lfsconfig').read_text().splitlines():
        key, sep, value = line.strip().partition('=')
        if sep and key.strip() == 'url' and value.strip():
          out.append(value.strip().removesuffix('/'))
          break
    except OSError:
      pass
    return out + [e for e in LFS_ENDPOINTS if e not in out]

  def fetch_shipped_model(self, progress=None, should_stop=None) -> Path | None:
    """Download the chosen large model if it is not here yet; None when nothing
    is chosen. The registry streams it to a .part file and hashes it on the way,
    so only the whole model ever takes the name."""
    from jetlink.registry.catalog import NetworkError
    from jetlink.registry.lfs import Pointer, lfs_download, lfs_resolve
    model = self.selected_model()
    if model is None or not model['oid']:
      return None
    dest = self.model_dir() / self.model_file_name(model)
    if dest.is_file() and dest.stat().st_size == model['size']:
      return dest
    pointer = Pointer(model['oid'], int(model['size']))
    for endpoint in self.lfs_endpoints():
      href = lfs_resolve(endpoint, pointer)
      if href is None:
        continue
      self.op.log.warning("jetlink: fetching the large model (%d MB) from %s", pointer.size >> 20, endpoint)
      return lfs_download(href, pointer, dest, progress=progress, should_stop=should_stop)
    raise NetworkError(f"no LFS server has {pointer.oid[:16]}")

  # -- the model manager's catalog --------------------------------------------

  def big_catalog(self, catalog: dict) -> dict:
    """The big-model catalog with every newer one sunnypilot has published folded in.
    A Jetson runs the commit's ONNX, so a model sunnypilot only builds for its next
    runtime is still one it can run; see jetlink.registry.catalog.fetch_catalogs.
    Never raises: a probe that fails keeps what the last one found."""
    try:
      from jetlink.registry.catalog import fetch_catalogs, merge_catalogs
      merged = merge_catalogs([catalog, fetch_catalogs()], selector=self.op.catalog_selector)
      added = len(merged.get('bundles', [])) - len(catalog.get('bundles', []))
      if added <= 0:
        return catalog
      self.op.log.warning("jetlink: %d model(s) only newer catalogs list", added)
      return merged
    except Exception:
      self.op.log.exception("jetlink: could not check for newer catalogs")
      return self._found_before(catalog)

  def _found_before(self, catalog: dict) -> dict:
    """The catalog with the models the last probe found folded in again, from the
    model manager's cached copy: every entry there the fetched catalog does not
    list. Not only merge_catalogs' entries with no artifacts: a newer catalog at
    the same selector version comes through with its builds (v26 lists Cinque
    Terre V3 that way). Dropped with a probe that failed, a pick only a newer
    catalog lists would be reset at the manager's next start and the owner would
    provision the default in its place; a refresh on a flaky network is enough.
    A model sunnypilot withdrew stays listed until a probe works."""
    try:
      listed = {b.get('ref') for b in catalog.get('bundles', [])}
      key = self.op.keys.catalog
      cached = ((self.op.get(key) if key else None) or {}).get('bundles', [])
      kept = [b for b in cached if isinstance(b, dict) and b.get('ref') not in listed]
    except Exception:
      return catalog
    if not kept:
      return catalog
    self.op.log.warning("jetlink: keeping %d model(s) the last probe found", len(kept))
    return {**catalog, 'bundles': [*catalog.get('bundles', []), *kept]}
