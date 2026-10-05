"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

sunnypilot's big-model catalog: which large models exist and which commit each one is.

The catalog is the same JSON the comma's model manager caches for its chestnut
slot, so a model picked here is a model the comma can ask for. A bundle's
artifacts are tinygrad pkls for a GPU we do not have; the only field that
matters is `ref`, the comma openpilot commit the bundle was compiled from,
because that commit's ONNX is what a jetlink server runs.

Stdlib only, and every network call takes an `opener` so tests stay offline.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass


CATALOG_URL_TEMPLATE = 'https://raw.githubusercontent.com/sunnypilot/sunnypilot-models/refs/heads/gh-pages/docs/driving_models_chestnut_v{version}.json'
# v26 is v25 plus Cinque Terre V3, at the same selector version. v27 onwards
# are selector 20 and a newer tinygrad, for sunnypilot's next sync.
CATALOG_VERSION = 26
CATALOG_URL = CATALOG_URL_TEMPLATE.format(version=CATALOG_VERSION)
# sunnypilot publishes a new catalog version for new models or a new runtime,
# and keeps the old ones. The versions after the pinned one are probed up to
# the first that is not there, so a model published later is listed without a
# release of this package. See merge_catalogs.
PROBE_LIMIT = 10
# The selector version the fork requires (REQUIRED_JSON_VERSION on the comma).
# It is a string in the JSON; bundles at any other version describe fields we
# would misread.
REQUIRED_SELECTOR_VERSION = 19
# Cinque Terre V3 Model (September 17, 2026)
DEFAULT_BIG_MODEL_REF = 'bf3e3631b3f91d92a1020a5e0dd4298b93ff4244'
# its name as sunnypilot's catalog lists it, without the build date: what a
# comma with no catalog to name it from shows (jetlink.openpilot, on a fork
# without sunnypilot's model manager)
DEFAULT_BIG_MODEL_NAME = 'Cinque Terre V3 Model'
CATALOG_TIMEOUT = 10.0

_REF = re.compile(r'[0-9a-f]{40}')
_SHA256 = re.compile(r'[0-9a-f]{64}')


class RegistryError(Exception):
  """Anything the registry refuses to do."""


class NetworkError(RegistryError):
  """A server could not be reached or did not answer sensibly."""


class VerifyError(RegistryError):
  """Bytes arrived, but not the bytes that were asked for."""


class NotFound(NetworkError):
  """The server answered that there is nothing at the URL."""


@dataclass(frozen=True)
class CatalogModel:
  name: str
  short_name: str
  ref: str
  build_time: str
  index: int


def is_ref(value: str) -> bool:
  """A comma openpilot commit: 40 lowercase hex characters."""
  return isinstance(value, str) and _REF.fullmatch(value) is not None


def is_sha256(value: str) -> bool:
  """A model identity: 64 lowercase hex characters, which is also the LFS oid."""
  return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def parse_catalog(data: dict) -> list[CatalogModel]:
  """The big-model bundles, newest first. No IO, and no bundle can raise.

  A malformed entry in a catalog served to every comma must cost that entry and
  nothing else, so each bundle is parsed in its own try.
  """
  found: dict[str, CatalogModel] = {}
  for bundle in _bundles(data):
    try:
      ref = bundle.get('ref')
      if not is_ref(ref) or ref in found:
        continue
      if _selector(bundle) != REQUIRED_SELECTOR_VERSION or not bundle.get('is_big'):
        continue
      found[ref] = CatalogModel(name=str(bundle.get('display_name') or ref[:10]), short_name=str(bundle.get('short_name') or ''),
                                ref=ref, build_time=str(bundle.get('build_time') or ''), index=int(bundle.get('index', 0)))
    except (AttributeError, TypeError, ValueError):
      continue
  return sorted(found.values(), key=lambda m: m.index, reverse=True)


def http_get(url: str, timeout: float, opener=None, limit: int = -1) -> bytes:
  """The body at `url`, at most `limit` bytes. A 404 is NotFound, and every
  other failure a NetworkError, so a caller only catches what it treats apart."""
  opener = opener or urllib.request.urlopen
  try:
    with opener(url, timeout=timeout) as response:
      return response.read(limit)
  except urllib.error.HTTPError as e:
    raise (NotFound if e.code == 404 else NetworkError)(f"could not fetch {url}: {e}") from e
  except (OSError, ValueError) as e:
    raise NetworkError(f"could not fetch {url}: {e}") from e


def http_json(url: str, timeout: float, opener=None, kind: type = dict):
  """http_get, parsed, and of the type asked for."""
  body = http_get(url, timeout, opener)
  try:
    data = json.loads(body.decode())
  except ValueError as e:
    raise NetworkError(f"{url} did not serve JSON: {e}") from e
  if not isinstance(data, kind):
    raise NetworkError(f"{url} did not serve a JSON {kind.__name__}")
  return data


def fetch_catalog(url: str = CATALOG_URL, timeout: float = CATALOG_TIMEOUT, opener=None) -> dict:
  """The catalog JSON. Every failure, transport or content, is a NetworkError."""
  return http_json(url, timeout, opener)


def fetch_catalogs(opener=None) -> dict:
  """The pinned catalog merged with every one sunnypilot has published since,
  whose commits the server runs too. The probe stops at the first version that
  is not there. Any other failure raises: a short list would drop a model
  found only past it from whatever the caller caches, so the caller keeps its
  last complete one instead."""
  found = [fetch_catalog(CATALOG_URL, opener=opener)]
  for v in range(CATALOG_VERSION + 1, CATALOG_VERSION + 1 + PROBE_LIMIT):
    try:
      found.append(fetch_catalog(CATALOG_URL_TEMPLATE.format(version=v), opener=opener))
    except NotFound:
      break
  return merge_catalogs(found)


def merge_catalogs(catalogs: list[dict], selector: int = REQUIRED_SELECTOR_VERSION) -> dict:
  """One catalog in the first one's shape, listing every big model of them all.

  A model some catalog lists at `selector` comes through as published, so a
  chestnut can still fetch its build. One listed only at another selector
  version, which is where sunnypilot puts every model once it moves runtimes,
  comes from the newest catalog that has it, retyped to `selector` and with no
  artifacts: an accelerator runs the commit's ONNX and needs nothing else from
  the entry, and a chestnut has nothing to download.
  """
  if not catalogs:
    return {}
  kept: dict[str, dict] = {}
  others: dict[str, dict] = {}
  for data in catalogs:
    for bundle in _bundles(data):
      ref = bundle.get('ref')
      if not is_ref(ref):
        continue
      if _selector(bundle) == selector:
        kept.setdefault(ref, bundle)
      elif bundle.get('is_big'):
        others[ref] = bundle   # the newest catalog's entry wins
  extra = [{**b, 'minimum_selector_version': str(selector), 'models': []} for ref, b in others.items() if ref not in kept]
  return {**catalogs[0], 'bundles': [*kept.values(), *extra]}


def _bundles(data: dict) -> list[dict]:
  bundles = data.get('bundles') if isinstance(data, dict) else None
  return [b for b in bundles if isinstance(b, dict)] if isinstance(bundles, list) else []


def _selector(bundle: dict) -> int | None:
  try:
    return int(bundle.get('minimum_selector_version', 0))
  except (TypeError, ValueError):
    return None
