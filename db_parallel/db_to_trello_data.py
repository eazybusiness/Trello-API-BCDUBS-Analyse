import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from db_parallel.trello_history_db import open_db_readonly


def build_latest_trello_like_data(db_path: str) -> Dict[str, Any]:
    """Build a trello_cards_detailed.json-like dict from the latest DB snapshot.

    This allows reusing existing report generators with minimal changes.
    """

    conn = open_db_readonly(Path(db_path))
    try:
        row = conn.execute("SELECT MAX(id) AS run_id FROM runs").fetchone()
        run_id = int(row["run_id"]) if row and row["run_id"] else 0
        if not run_id:
            return {"board": {}, "custom_fields": [], "cards_by_list": {}}

        board_row = conn.execute(
            """
            SELECT board_id, board_name
            FROM cards
            WHERE last_seen_run_id = ?
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()

        board = {
            "id": (board_row["board_id"] if board_row else None),
            "name": (board_row["board_name"] if board_row else None),
            "desc": "",
        }

        cards_by_list: Dict[str, List[dict]] = defaultdict(list)

        rows = conn.execute(
            """
            SELECT list_name, raw_json
            FROM cards
            WHERE last_seen_run_id = ? OR archived = 1
            """,
            (run_id,),
        ).fetchall()

        for r in rows:
            list_name = r["list_name"] or "Unknown"
            raw = r["raw_json"]
            if not raw:
                continue
            try:
                card = json.loads(raw)
            except Exception:
                continue
            if isinstance(card, dict):
                cards_by_list[list_name].append(card)

        return {
            "board": board,
            "custom_fields": [],
            "cards_by_list": dict(cards_by_list),
        }
    finally:
        conn.close()
