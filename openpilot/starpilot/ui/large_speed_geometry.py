"""Large speed stack dimensions shared by rendering, input and layout metadata."""

WIDTH = 320
MAX_ROW_HEIGHT = 210
LIMIT_ROW_HEIGHT = 260
CARD_HEIGHT = MAX_ROW_HEIGHT + LIMIT_ROW_HEIGHT
ACTION_HEIGHT = 108
ACTION_X = 88
ACTION_Y = 75 + CARD_HEIGHT + 22
ACTION_HEADER_HEIGHT = 44
GAP = 8
SOURCE_ROW_HEIGHT = 76
PADDING = 24


def card_height(mode):
  return CARD_HEIGHT if mode == 'split' else LIMIT_ROW_HEIGHT if mode == 'limit_only' else MAX_ROW_HEIGHT


def sources_extent(document):
  """Extra height the cruise widget takes for speed-limit sources: a row in the card, or a small card of its own below."""
  if document.get('speedSources') is not True:
    return 0
  return GAP + SOURCE_ROW_HEIGHT if document.get('speedSourcesCard') is True else SOURCE_ROW_HEIGHT
