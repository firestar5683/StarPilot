import os
import requests


# Forks can host the public segment dataset on Hugging Face.
COMMA_CAR_SEGMENTS_REPO = os.environ.get("COMMA_CAR_SEGMENTS_REPO", "https://huggingface.co/datasets/commaai/commaCarSegments")
COMMA_CAR_SEGMENTS_BRANCH = os.environ.get("COMMA_CAR_SEGMENTS_BRANCH", "main")

def get_comma_car_segments_database():
  from opendbc.car.fingerprints import MIGRATION

  database = requests.get(get_repo_raw_url("database.json")).json()

  ret = {}
  for platform in database:
    # TODO: remove this when commaCarSegments is updated to remove selector
    ret[MIGRATION.get(platform, platform)] = [s.rstrip('/s') for s in database[platform]]

  return ret


# Helpers related to interfacing with the commaCarSegments repository, which contains a collection of public segments for users to perform validation on.

def get_repo_raw_url(path):
  if "huggingface" in COMMA_CAR_SEGMENTS_REPO:
    return f"{COMMA_CAR_SEGMENTS_REPO}/raw/{COMMA_CAR_SEGMENTS_BRANCH}/{path}"

def get_repo_url(path):
  # Hugging Face resolves actual artifact bytes over ordinary HTTP.
  if "huggingface" in COMMA_CAR_SEGMENTS_REPO:
    return f"{COMMA_CAR_SEGMENTS_REPO}/resolve/{COMMA_CAR_SEGMENTS_BRANCH}/{path}"
  raise ValueError("segment dataset must provide a Hugging Face resolve endpoint")


def get_url(route, segment, file="rlog.zst"):
  return get_repo_url(f"segments/{route.replace('|', '/')}/{segment}/{file}")
