from collections import OrderedDict
from enum import IntEnum
from functools import cmp_to_key
import itertools
import json
import sys

POSITIONS = ["btn", "sb", "bb", "utg", "mp", "co"]

CONFIG_KEYS = [*POSITIONS, "board", "dead"]

SUITS = ["h", "d", "s", "c"]
CARDINALITIES = ["2", "3", "4", "5", "6",
                 "7", "8", "9", "T", "J", "Q", "K", "A"]
CARDS = {c + s for s in SUITS for c in CARDINALITIES}

TABLE = "./db/table.json"


def get_cardinality_strength(cardinality):
  assert cardinality in CARDINALITIES
  return CARDINALITIES.index(cardinality)


class Hand(IntEnum):
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
  records = sorted([(cardinality, record)
                   for cardinality, record in freqs.items()], key=lambda tuple: -get_cardinality_strength(tuple[0]))
  for cardinality, record in records:
    if record['count'] == n:
      return record['cards']
  return None


def get_pair(cards):
  maybe_pair = get_n_of_kind(cards, 2)
  if maybe_pair is None:
    return None
  kickers = get_high_card(list(set(cards) - set(maybe_pair)))
  return [*maybe_pair, *kickers]


def get_two_pair(cards):
  maybe_first_pair = get_n_of_kind(cards, 2)
  if maybe_first_pair is None:
    return None
  remaining_cards = list(set(cards) - set(maybe_first_pair))
  maybe_second_pair = get_n_of_kind(remaining_cards, 2)
  if maybe_second_pair is None:
    return None
  kickers = get_high_card(list(set(remaining_cards) - set(maybe_second_pair)))
  return [*maybe_first_pair, *maybe_second_pair, kickers[0]]


def get_three_of_kind(cards):
  maybe_triple = get_n_of_kind(cards, 3)
  if maybe_triple is None:
    return None
  kickers = get_high_card(list(set(cards) - set(maybe_triple)))
  return [*maybe_triple, *kickers[:2]]


def get_full_house(cards):
  maybe_triple = get_n_of_kind(cards, 3)
  if maybe_triple is None:
    return None
  maybe_pair = get_n_of_kind(list(set(cards) - set(maybe_triple)), 2)
  if maybe_pair is None:
    return None
  return [*maybe_triple, *maybe_pair]


def get_quads(cards):
  maybe_quads = get_n_of_kind(cards, 4)
  if maybe_quads is None:
    return None
  kickers = get_high_card(list(set(cards) - set(maybe_quads)))
  return [*maybe_quads, kickers[0]]


def get_flush(cards):
  suit_freqs = {}
  sorted_cards = sorted(
      cards, key=lambda card: -get_cardinality_strength(card[0]))
  for card in sorted_cards:
    suit = card[1]
    if suit in suit_freqs:
      record = suit_freqs[suit]
      record["count"] += 1
      record['cards'].append(card)
    else:
      suit_freqs[suit] = {'count': 1, 'cards': [card]}
  for record in suit_freqs.values():
    if record['count'] == 5:
      return record['cards']
  return None


def get_straight(cards):
  sorted_cards = sorted(
      cards, key=lambda card: -get_cardinality_strength(card[0]))
  made_straight = [sorted_cards[0]]
  for i in range(1, len(sorted_cards)):
    gap = get_cardinality_strength(
        sorted_cards[i-1][0]) - get_cardinality_strength(sorted_cards[i][0])
    if gap == 0:
      continue
    elif gap == 1:
      made_straight.append(sorted_cards[i])
    else:
      # We only want to reset the made straight if we haven't found one yet.
      # In the case where we already found a straight, we need to leave it.
      if len(made_straight) < 5:
        made_straight = [sorted_cards[i]]

  # Check for low-Ace straight.
  if sorted_cards[-1][0] == "2" and sorted_cards[0][0] == "A":
    made_straight.append(sorted_cards[0])

  if len(made_straight) >= 5:
    return made_straight[:5]
  return None


def get_straight_flush(cards):
  suit_groups = {}
  for card in cards:
    suit = card[1]
    if suit in suit_groups:
      suit_groups[suit].append(card)
    else:
      suit_groups[suit] = [card]
  for group in suit_groups.values():
    # `get_straight` always returns the best straight so even if there is more
    # than one straight flush, we get the best one here. Moreover, there can
    # never be straight flushes from distinct suits since there are at most 7
    # cards to choose from.
    maybe_straight_flush = get_straight(group)
    if maybe_straight_flush:
      return maybe_straight_flush
  return None


def get_royal_flush(cards):
  maybe_straight_flush = get_straight_flush(cards)
  if not maybe_straight_flush:
    return None
  # The most valuable card in the straight flush is always first.
  if maybe_straight_flush[0][0] == "A":
    return maybe_straight_flush
  return None


def get_high_card(cards):
  length = min(5, len(cards))
  return sorted(
      cards, key=lambda card: -get_cardinality_strength(card[0]))[:length]


HANDS = OrderedDict([
    (Hand.ROYAL_FLUSH, {"calc": get_royal_flush, "tiebreakers": []}),
    (Hand.STRAIGHT_FLUSH, {"calc": get_straight_flush, "tiebreakers": []}),
    (Hand.QUADS, {"calc": get_quads, "tiebreakers": [0, 4]}),
    (Hand.FULL_HOUSE, {"calc": get_full_house,  "tiebreakers": [0, 3]}),
    (Hand.FLUSH, {"calc": get_flush,  "tiebreakers": [0]}),
    (Hand.STRAIGHT, {"calc": get_straight, "tiebreakers": [0]}),
    (Hand.THREE_OF_KIND, {
     "calc": get_three_of_kind, "tiebreakers": [0, 3, 4]}),
    (Hand.TWO_PAIR, {"calc": get_two_pair, "tiebreakers": [0, 2, 4]}),
    (Hand.PAIR, {"calc": get_pair, "tiebreakers": [0, 2, 3, 4]}),
    (Hand.HIGH_CARD, {"calc": get_high_card, "tiebreakers": [0, 1, 2, 3, 4]}),
])


def compare_hands(lhs, rhs):
  if lhs['id'] != rhs['id']:
    return -1 if lhs['id'] > rhs['id'] else 1
  for i in HANDS[lhs['id']]['tiebreakers']:
    gap = get_cardinality_strength(
        lhs['cards'][i][0]) - get_cardinality_strength(rhs['cards'][i][0])
    if gap == 0:
      # They're the same card so we need to check the next tiebreaker.
      continue
    if gap > 0:
      return -1
    else:
      return 1
  return 0


def get_best_hand(cards):
  global CACHE
  global SHOULD_WRITE_CACHE
  key = ''.join(sorted(cards))
  if key in CACHE:
    return CACHE[key]
  for id, record in HANDS.items():
    maybe_hand = record["calc"](cards)
    if maybe_hand:
      SHOULD_WRITE_CACHE = True
      CACHE[key] = {"id": id, "cards": maybe_hand}
      return CACHE[key]
  assert False, "Jake fucked up the code."


def get_result(board, players):
  hands = []
  for position, record in players.items():
    hands.append(
        (position, get_best_hand([*record['hand'], *board])))
  sorted_hands = sorted(hands, key=cmp_to_key(
      lambda lhs, rhs: compare_hands(lhs[1], rhs[1])))
  assert len(sorted_hands) >= 2, "Got result with less than 2 hands."
  rank = 0
  result = [{'rank': rank, 'player': sorted_hands[0]
             [0], 'hand': sorted_hands[0][1]}]
  for i in range(1, len(sorted_hands)):
    compared = compare_hands(sorted_hands[i-1][1], sorted_hands[i][1])
    if compared != 0:
      rank += 1
    result.append(
        {'rank': rank, 'player': sorted_hands[i][0], 'hand': sorted_hands[i][1]})
  return result


def calculate_equities(players, total_outcomes):
  equities = {}
  for position, record in players.items():
    win_rate = record['wins'] / total_outcomes
    tie_rate = record['ties'] / total_outcomes
    equities[position] = {'win': win_rate, 'tie': tie_rate}
  return equities


def load_table():
  global CACHE
  global SHOULD_WRITE_CACHE
  print("loading cache... ", end='')
  with open(TABLE, "r") as f:
    CACHE = json.load(f)
    SHOULD_WRITE_CACHE = False
  print("done.")


def store_tables():
  if not SHOULD_WRITE_CACHE:
    return
  print("writing cache... ", end='')
  with open(TABLE, "w") as f:
    json.dump(CACHE, f, indent=4)
  print("done.")


def load_spots():
  with open("./db/spots.json", "r") as f:
    return json.load(f)


def hash_config(config):
  items = [item for key, value in sorted(
      config.items()) for item in sorted(value)]
  print(items)
  key = 0
  return key


def main():
  if len(sys.argv) != 2:
    print("usage: python main.py <config>")
    exit(1)

  config = read_config(sys.argv[1])
  spots = load_spots()
  config_key = hash_config(config)
  exit(1)
  alive = alive_cards(config)

  load_table()
  players = {pos: {'hand': hand, 'wins': 0, 'ties': 0} for pos, hand in config.items(
  ) if pos in POSITIONS and len(hand) == 2}
  outcomes = 0

  known_board = config['board']
  if len(known_board) == 5:
    # The board is complete so there are no combinations to test.
    result = get_result(known_board, players)
    outcomes = 1
  else:
    for comb in itertools.combinations(alive, 5 - len(known_board)):
      result = get_result([*known_board, *comb], players)
      winners = [record for record in result if record['rank'] == 0]
      assert len(winners) > 0
      outcome_key = 'ties' if len(winners) > 1 else 'wins'
      for winner in winners:
        players[winner['player']][outcome_key] += 1
      outcomes += 1

  equities = calculate_equities(players, outcomes)
  for pos, equity in equities.items():
    print(
        f"{players[pos]['hand']} -->\n win={(100 * equity['win']):.2f}\n tie={(100 * equity['tie']):.2f}")

  store_table()


if __name__ == "__main__":
  main()
