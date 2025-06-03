from enum import Enum
import itertools
import json
import sys

POSITIONS = ["btn", "sb", "bb", "utg", "mp", "co"]

CONFIG_KEYS = [*POSITIONS, "board", "dead"]

SUITS = ["h", "d", "s", "c"]
CARDINALITIES = ["2", "3", "4", "5", "6",
                 "7", "8", "9", "T", "J", "Q", "K", "A"]
CARDS = {c + s for s in SUITS for c in CARDINALITIES}


class Hand(Enum):
  ROYAL_FLUSH = 10
  STRAIGHT_FLUSH = 9
  QUADS = 8
  FULL_HOUSE = 7
  FLUSH = 6
  STRAIGHT = 5
  THREE_OF_KIND = 4
  TWO_PAIR = 3
  PAIR = 2
  HIGH_CARD = 1


def validate_config(config):
  for key in CONFIG_KEYS:
    if key not in config:
      print(f"Config missing key '{key}'.")
      exit(1)
  seen_cards = {}
  count_players = 0
  for key, values in config.items():
    if key not in CONFIG_KEYS:
      print(f"Config contains unknown key '{key}'.")
      exit(1)
    values_count = len(values)
    if key in POSITIONS:
      if values_count != 0 and values_count != 2:
        print(
            f"Position '{key}' must either have 0 or 2 cards in the hole. Has: {values_count}.")
        exit(1)
      if values_count == 2:
        count_players += 1
    elif key == "board" and values_count > 5:
      print(f"'board' has too many cards: {values_count}.")
      exit(1)
    for card in values:
      if card not in CARDS:
        print(f"Uknown card '{card}' in '{key}'.")
        exit(1)
      if card in seen_cards:
        print(
            f"'{card}' in '{key}' is a duplicate (also in '{seen_cards[card]}').")
        exit(1)
      seen_cards[card] = key
  if count_players <= 1:
    print(f"Can't calculate equity with a {count_players}-player spot.")
    exit(1)


def read_config(file_path):
  with open(file_path, "r") as f:
    config = json.load(f)
    validate_config(config)
    return config


def alive_cards(config):
  dead = set()
  for cards in config.values():
    dead.update(cards)
  print(dead)
  return CARDS - dead


def get_n_of_kind(cards, n):
  freqs = {}
  for c in cards:
    cardinality = c[0]
    if cardinality in freqs:
      record = freqs[cardinality]
      record['count'] += 1
      record['cards'].append(c)
    else:
      freqs[cardinality] = {'count': 1, 'cards': [c]}
  for cardinality, record in freqs.items():
    print(cardinality, record)
  return None


def get_pair(cards):
  return get_n_of_kind(cards, 2)


def get_two_pair(cards):
  first_pair = get_pair(cards)
  if first_pair is None:
    return None
  # Remove first pair then try again.
  return None


def get_three_of_kind(cards):
  return None


def get_full_house(cards):
  return None


def get_quads(cards):
  return None


def get_flush(cards):
  return None


def get_straight(cards):
  return None


def get_straight_flush(cards):
  return None


def get_royal_flush(cards):
  return None


def get_high_card(cards):
  return None


HAND_CALCULATORS = [
    {"calc": get_royal_flush, "id": Hand.ROYAL_FLUSH},
    {"calc": get_straight_flush, "id": Hand.STRAIGHT_FLUSH},
    {"calc": get_quads, "id": Hand.QUADS},
    {"calc": get_full_house, "id": Hand.FULL_HOUSE},
    {"calc": get_flush, "id": Hand.FLUSH},
    {"calc": get_straight, "id": Hand.STRAIGHT},
    {"calc": get_three_of_kind, "id": Hand.THREE_OF_KIND},
    {"calc": get_two_pair, "id": Hand.TWO_PAIR},
    {"calc": get_pair, "id": Hand.PAIR},
    {"calc": get_high_card, "id": Hand.HIGH_CARD},
]


def get_best_hand(cards):
  print("getting best hand from", cards)
  for hand in HAND_CALCULATORS:
    maybe_hand = hand["calc"](cards)
    if maybe_hand:
      return maybe_hand
  assert False, "Jake fucked up the code."


def get_result(board, config):
  players = [key for key, values in config.items(
  ) if key in POSITIONS and len(values) == 2]
  print(players)
  for player in players:
    get_best_hand([*config[player], *board])
  return (players[0],)


def main():
  if len(sys.argv) != 2:
    print("usage: python main.py <config>")
    exit(1)

  config = read_config(sys.argv[1])
  alive = alive_cards(config)
  print(alive)

  known_board = config['board']
  if len(known_board) == 5:
    # Run through checker.
    result = get_result(known_board, config)
    print(result)
    return

  for comb in itertools.combinations(alive, 5 - len(known_board)):
    result = get_result([*known_board, *comb], config)
    print(result)


if __name__ == "__main__":
  main()
