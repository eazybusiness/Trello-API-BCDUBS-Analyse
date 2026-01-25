import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pytz


GERMAN_TZ = pytz.timezone("Europe/Berlin")


@dataclass(frozen=True)
class RunInfo:
    run_id: int
    fetched_at_utc: str
    source_sha256: str


def _parse_trello_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _now_berlin() -> datetime:
    return datetime.now(GERMAN_TZ)


def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _open_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fetched_at_utc TEXT NOT NULL,
            source_sha256 TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cards (
            card_id TEXT PRIMARY KEY,
            board_id TEXT,
            board_name TEXT,
            list_name TEXT,
            name TEXT,
            short_url TEXT,
            due_utc TEXT,
            closed INTEGER NOT NULL DEFAULT 0,
            archived INTEGER NOT NULL DEFAULT 0,
            last_seen_run_id INTEGER,
            last_seen_at_utc TEXT
        );

        CREATE TABLE IF NOT EXISTS checklist_items (
            check_item_id TEXT PRIMARY KEY,
            card_id TEXT NOT NULL,
            checklist_id TEXT,
            checklist_name TEXT,
            item_name TEXT,
            actor TEXT,
            state TEXT,
            last_seen_run_id INTEGER,
            last_seen_at_utc TEXT,
            FOREIGN KEY(card_id) REFERENCES cards(card_id)
        );

        CREATE TABLE IF NOT EXISTS late_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            card_id TEXT NOT NULL,
            check_item_id TEXT,
            actor TEXT,
            due_utc TEXT NOT NULL,
            detected_at_utc TEXT NOT NULL,
            minutes_late INTEGER NOT NULL,
            days_late INTEGER NOT NULL,
            list_name TEXT,
            card_name TEXT,
            short_url TEXT,
            UNIQUE(run_id, card_id, check_item_id),
            FOREIGN KEY(run_id) REFERENCES runs(id),
            FOREIGN KEY(card_id) REFERENCES cards(card_id)
        );
        """
    )
    conn.commit()


def start_run(conn: sqlite3.Connection, source_bytes: bytes, fetched_at_utc: Optional[str] = None) -> RunInfo:
    if fetched_at_utc is None:
        fetched_at_utc = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    sha = _sha256_bytes(source_bytes)
    cur = conn.execute(
        "INSERT INTO runs (fetched_at_utc, source_sha256) VALUES (?, ?)",
        (fetched_at_utc, sha),
    )
    conn.commit()
    return RunInfo(run_id=int(cur.lastrowid), fetched_at_utc=fetched_at_utc, source_sha256=sha)


def _iter_cards(data: dict) -> Iterable[Tuple[str, dict]]:
    cards_by_list = (data.get("cards_by_list") or {})
    for list_name, cards in cards_by_list.items():
        if not isinstance(cards, list):
            continue
        for c in cards:
            if isinstance(c, dict):
                yield list_name, c


def _detect_actor(item_name: str, speaker_names: List[str]) -> Optional[str]:
    haystack = (item_name or "").lower()
    for name in speaker_names:
        if name.lower() in haystack:
            return name
    return None


def ingest_trello_cards(
    db_path: str,
    trello_json_path: str = "trello_cards_detailed.json",
    speaker_names: Optional[List[str]] = None,
) -> RunInfo:
    json_path = Path(trello_json_path)
    source_bytes = json_path.read_bytes()
    data = json.loads(source_bytes.decode("utf-8"))

    if speaker_names is None:
        speaker_names = []

    conn = _open_db(Path(db_path))
    try:
        init_db(conn)
        run = start_run(conn, source_bytes=source_bytes)

        board = data.get("board") or {}
        board_id = board.get("id")
        board_name = board.get("name")

        now_utc = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

        seen_card_ids: List[str] = []

        for list_name, card in _iter_cards(data):
            card_id = str(card.get("id") or "")
            if not card_id:
                continue

            seen_card_ids.append(card_id)

            conn.execute(
                """
                INSERT INTO cards (
                    card_id, board_id, board_name, list_name, name, short_url,
                    due_utc, closed, archived, last_seen_run_id, last_seen_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                ON CONFLICT(card_id) DO UPDATE SET
                    board_id=excluded.board_id,
                    board_name=excluded.board_name,
                    list_name=excluded.list_name,
                    name=excluded.name,
                    short_url=excluded.short_url,
                    due_utc=excluded.due_utc,
                    closed=excluded.closed,
                    archived=0,
                    last_seen_run_id=excluded.last_seen_run_id,
                    last_seen_at_utc=excluded.last_seen_at_utc
                """,
                (
                    card_id,
                    board_id,
                    board_name,
                    list_name,
                    card.get("name"),
                    card.get("shortUrl") or card.get("url"),
                    card.get("due"),
                    1 if card.get("closed") else 0,
                    run.run_id,
                    now_utc,
                ),
            )

            for checklist in (card.get("checklists") or []):
                checklist_id = str(checklist.get("id") or "")
                checklist_name = checklist.get("name")
                for item in (checklist.get("checkItems") or []):
                    check_item_id = str(item.get("id") or "")
                    if not check_item_id:
                        continue
                    item_name = item.get("name")
                    state = (item.get("state") or "").lower() or "incomplete"
                    actor = _detect_actor(item_name or "", speaker_names)

                    conn.execute(
                        """
                        INSERT INTO checklist_items (
                            check_item_id, card_id, checklist_id, checklist_name,
                            item_name, actor, state, last_seen_run_id, last_seen_at_utc
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(check_item_id) DO UPDATE SET
                            card_id=excluded.card_id,
                            checklist_id=excluded.checklist_id,
                            checklist_name=excluded.checklist_name,
                            item_name=excluded.item_name,
                            actor=excluded.actor,
                            state=excluded.state,
                            last_seen_run_id=excluded.last_seen_run_id,
                            last_seen_at_utc=excluded.last_seen_at_utc
                        """,
                        (
                            check_item_id,
                            card_id,
                            checklist_id or None,
                            checklist_name,
                            item_name,
                            actor,
                            state,
                            run.run_id,
                            now_utc,
                        ),
                    )

                    due_dt_utc = _parse_trello_datetime(card.get("due") or "")
                    if due_dt_utc is None:
                        continue

                    now_berlin = _now_berlin()
                    due_berlin = due_dt_utc.astimezone(GERMAN_TZ)

                    if state != "complete" and now_berlin > due_berlin:
                        minutes_late = int((now_berlin - due_berlin).total_seconds() // 60)
                        days_late = int(minutes_late // (60 * 24))
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO late_events (
                                run_id, card_id, check_item_id, actor, due_utc,
                                detected_at_utc, minutes_late, days_late,
                                list_name, card_name, short_url
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                run.run_id,
                                card_id,
                                check_item_id,
                                actor,
                                card.get("due"),
                                now_utc,
                                minutes_late,
                                days_late,
                                list_name,
                                card.get("name"),
                                card.get("shortUrl") or card.get("url"),
                            ),
                        )

        if seen_card_ids:
            placeholders = ",".join(["?"] * len(seen_card_ids))
            conn.execute(
                f"UPDATE cards SET archived=1 WHERE archived=0 AND card_id NOT IN ({placeholders})",
                tuple(seen_card_ids),
            )
        else:
            conn.execute("UPDATE cards SET archived=1 WHERE archived=0")

        conn.commit()
        return run
    finally:
        conn.close()


def latest_late_events(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    row = conn.execute("SELECT MAX(id) AS max_id FROM runs").fetchone()
    run_id = (row["max_id"] if row else None)
    if not run_id:
        return []

    return list(
        conn.execute(
            """
            SELECT *
            FROM late_events
            WHERE run_id = ?
            ORDER BY minutes_late DESC
            """,
            (run_id,),
        ).fetchall()
    )


def open_db_readonly(db_path: str) -> sqlite3.Connection:
    p = Path(db_path)
    conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn
