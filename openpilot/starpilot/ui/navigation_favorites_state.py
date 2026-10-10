"""Shared visibility for projected favorite drawing and touch handling."""

FAVORITES = ('nav_home', 'nav_work')


def active_favorite(document, placements):
  if not document or not document['destination']:
    return None
  for key in FAVORITES:
    placed = placements.get(key)
    if placed and placed['enabled'] and any(
        row.get('label') == key.removeprefix('nav_') and row['id'] == document['destination']['id']
        for row in document['favorites']):
      return key
  return None


def favorite_visible(key, document, placements):
  active = active_favorite(document, placements)
  return active is None or key == active
