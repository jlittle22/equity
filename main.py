import json
import sys

CONFIG_KEYS = ["btn", "sb", "bb", "utg", "mp", "co", "board", "dead"]

SUITS = ["h", "d", "s", "c"]
CARDINALITIES = ["2", "3", "4", "5", "6",
                 "7", "8", "9", "T", "J", "Q", "K", "A"]
CARDS = {c + s for s in SUITS for c in CARDINALITIES}


def validate_config(config):
  for key in CONFIG_KEYS:
    if key not in config:
      print(f"Config missing key '{key}'.")
      exit(1)
  for key, values in config.keys():
    if key not in CONFIG_KEYS:
      print(f"Config contains unknown key '{key}'.")
      exit(1)


def read_config(file_path):
  with open(file_path, "r") as f:
    config = json.load(f)
    validate_config(config)
    return config


def main():
  if len(sys.argv) != 2:
    print("usage: python main.py <config>")
    exit(1)

  config = read_config(sys.argv[1])
  print(config)
  print(CARDS)


if __name__ == "__main__":
  main()
