import argparse
from datetime import datetime

from db_parallel.generate_completed_report_db import main as completed_main
from db_parallel.generate_late_report_db import main as late_main
from db_parallel.generate_workload_report_db import main as workload_main
from db_parallel.trello_history_db import ingest_trello_data
from speaker_profiles import SPEAKER_PROFILES
from trello_client import TrelloClient


def main() -> int:
    parser = argparse.ArgumentParser(description="DB-parallel pipeline: ingest Trello via API -> SQLite, then generate 3 HTML reports from DB.")
    parser.add_argument("--board", default="True Crime Video Dubs", help="Trello board name")
    parser.add_argument("--db", default="db_parallel/data/trello_history.sqlite", help="SQLite DB path")
    args = parser.parse_args()

    client = TrelloClient()
    result = client.get_board_cards_with_lists(args.board)

    fetched_at_utc = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    speaker_names = list(SPEAKER_PROFILES.keys())
    ingest_trello_data(db_path=args.db, data=result, speaker_names=speaker_names, fetched_at_utc=fetched_at_utc)

    workload_main()
    completed_main()
    late_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
