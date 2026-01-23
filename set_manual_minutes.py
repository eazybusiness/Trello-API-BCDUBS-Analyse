import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _load_cache(path: Path) -> Dict[str, int]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            out: Dict[str, int] = {}
            for k, v in data.items():
                try:
                    out[str(k)] = int(v)
                except Exception:
                    continue
            return out
    except Exception:
        return {}
    return {}


def _save_cache(path: Path, cache: Dict[str, int]) -> None:
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _find_cards(data: dict, query: str) -> List[Tuple[str, str, str]]:
    q = query.lower().strip()
    matches: List[Tuple[str, str, str]] = []

    cards_by_list = data.get("cards_by_list") or {}
    for list_name, cards in cards_by_list.items():
        for c in cards or []:
            if not isinstance(c, dict):
                continue
            card_id = str(c.get("id") or "").strip()
            name = str(c.get("name") or "").strip()
            if not card_id or not name:
                continue
            if q in name.lower():
                matches.append((list_name, card_id, name))

    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description="Set manual video minutes for a project into video_length_cache.json")
    parser.add_argument("--query", required=True, help="Project name (substring match), e.g. IB36")
    parser.add_argument("--minutes", required=True, type=int, help="Minutes to store (integer)")
    parser.add_argument("--json", dest="json_path", default="trello_cards_detailed.json", help="Path to trello_cards_detailed.json")
    parser.add_argument("--cache", dest="cache_path", default="video_length_cache.json", help="Path to video_length_cache.json")
    parser.add_argument("--pick", dest="pick", type=int, default=1, help="If multiple matches, pick the Nth match (1-based)")
    args = parser.parse_args()

    json_path = Path(args.json_path)
    cache_path = Path(args.cache_path)

    if args.minutes <= 0:
        print("ERROR: minutes must be > 0", file=sys.stderr)
        return 2

    if not json_path.exists():
        print(f"ERROR: JSON file not found: {json_path}", file=sys.stderr)
        return 1

    data = _read_json(json_path)
    matches = _find_cards(data, args.query)

    if not matches:
        print(f"No cards matched query: {args.query}", file=sys.stderr)
        return 3

    print(f"Found {len(matches)} match(es) for '{args.query}':")
    for idx, (list_name, card_id, name) in enumerate(matches, start=1):
        print(f"{idx}. [{list_name}] {name} (id={card_id})")

    pick = args.pick
    if pick < 1 or pick > len(matches):
        print(f"ERROR: --pick must be between 1 and {len(matches)}", file=sys.stderr)
        return 4

    list_name, card_id, name = matches[pick - 1]

    cache = _load_cache(cache_path)
    cache[card_id] = int(args.minutes)
    _save_cache(cache_path, cache)

    print(f"Saved minutes: {args.minutes} for card '{name}' (id={card_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
