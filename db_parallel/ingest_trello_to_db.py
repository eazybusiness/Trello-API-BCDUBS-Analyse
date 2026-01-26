import argparse
from datetime import datetime
from pathlib import Path

from trello_client import TrelloClient

from db_parallel.trello_history_db import ingest_trello_data
from speaker_profiles import SPEAKER_PROFILES


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Trello data via API and upsert into SQLite history DB (parallel DB-first pipeline).")
    parser.add_argument("--db", default="db_parallel/data/trello_history.sqlite", help="SQLite DB path")
    parser.add_argument("--board", default="True Crime Video Dubs", help="Trello board name")
    args = parser.parse_args()

    client = TrelloClient()
    result = client.get_board_cards_with_lists(args.board)

    fetched_at_utc = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    speaker_names = list(SPEAKER_PROFILES.keys())

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    run = ingest_trello_data(db_path=str(db_path), data=result, speaker_names=speaker_names, fetched_at_utc=fetched_at_utc)
    print(f"DB ingest complete. run_id={run.run_id} fetched_at_utc={run.fetched_at_utc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
