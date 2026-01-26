from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pytz

from db_parallel.trello_history_db import open_db_readonly


GERMAN_TZ = pytz.timezone("Europe/Berlin")


def _get_german_time() -> datetime:
    return datetime.now(GERMAN_TZ)


def _fmt_minutes(minutes: int) -> str:
    if minutes < 0:
        minutes = 0
    days = minutes // (60 * 24)
    rem = minutes % (60 * 24)
    hours = rem // 60
    mins = rem % 60
    if days > 0:
        return f"{days}d {hours}h {mins}m"
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def _html_escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def generate_late_report_from_db(
    db_path: str = "db_parallel/data/trello_history.sqlite",
    output_file: str = "db_parallel/reports/late_report.html",
) -> str:
    conn = open_db_readonly(Path(db_path))
    try:
        row = conn.execute("SELECT MAX(id) AS run_id FROM runs").fetchone()
        run_id = int(row["run_id"]) if row and row["run_id"] else 0
        if not run_id:
            late_events = []
        else:
            late_events = list(
                conn.execute(
                    """
                    SELECT actor, card_id, card_name, short_url, due_utc, minutes_late, days_late, list_name
                    FROM late_events
                    WHERE run_id = ?
                    ORDER BY minutes_late DESC
                    """,
                    (run_id,),
                ).fetchall()
            )

        by_actor: Dict[str, List[dict]] = defaultdict(list)
        by_card: Dict[str, List[dict]] = defaultdict(list)

        for ev in late_events:
            actor = ev["actor"] or "(unknown)"
            item = {
                "actor": actor,
                "card_id": ev["card_id"],
                "card_name": ev["card_name"] or "(unnamed)",
                "short_url": ev["short_url"] or "",
                "due_utc": ev["due_utc"],
                "minutes_late": int(ev["minutes_late"]),
                "days_late": int(ev["days_late"]),
                "list_name": ev["list_name"] or "",
            }
            by_actor[actor].append(item)
            by_card[item["card_id"]].append(item)

        actor_stats = []
        for actor, items in by_actor.items():
            total = len(items)
            worst = max(i["minutes_late"] for i in items) if items else 0
            actor_stats.append((actor, total, worst))
        actor_stats.sort(key=lambda x: (x[1], x[2]), reverse=True)

        now_de = _get_german_time().strftime("%Y-%m-%d %H:%M:%S")

        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        def card_row(it: dict) -> str:
            name = _html_escape(it["card_name"])
            url = _html_escape(it["short_url"])
            actor = _html_escape(it["actor"])
            due = _html_escape(it["due_utc"] or "")
            late = _fmt_minutes(it["minutes_late"])
            list_name = _html_escape(it["list_name"])
            link_html = f"<a class=\"text-blue-600 hover:underline\" href=\"{url}\" target=\"_blank\" rel=\"noopener noreferrer\">Open</a>" if url else ""
            return f"""
                <tr class=\"border-t\">
                    <td class=\"px-4 py-3 font-medium\">{name}</td>
                    <td class=\"px-4 py-3\">{actor}</td>
                    <td class=\"px-4 py-3\">{list_name}</td>
                    <td class=\"px-4 py-3 font-mono text-sm\">{due}</td>
                    <td class=\"px-4 py-3\"><span class=\"inline-flex px-2 py-1 rounded bg-red-100 text-red-800 text-sm\">{late}</span></td>
                    <td class=\"px-4 py-3\">{link_html}</td>
                </tr>
            """

        project_rows = []
        for _, items in by_card.items():
            for it in sorted(items, key=lambda x: x["minutes_late"], reverse=True):
                project_rows.append(card_row(it))

        actor_rows = []
        for actor, total, worst in actor_stats:
            actor_rows.append(
                f"""
                <tr class=\"border-t\">
                    <td class=\"px-4 py-3 font-medium\">{_html_escape(actor)}</td>
                    <td class=\"px-4 py-3\">{total}</td>
                    <td class=\"px-4 py-3\"><span class=\"inline-flex px-2 py-1 rounded bg-red-100 text-red-800 text-sm\">{_fmt_minutes(int(worst))}</span></td>
                </tr>
                """
            )

        total_late = len(late_events)
        total_late_projects = len(by_card)

        html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Late Report (DB Parallel)</title>
    <script src=\"https://cdn.tailwindcss.com\"></script>
</head>
<body class=\"bg-gray-50\">
    <div class=\"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8\">
        <div class=\"bg-white rounded-lg shadow p-6 my-8\">
            <h1 class=\"text-2xl font-bold text-gray-900\">⏰ Late Report (DB Parallel)</h1>
            <p class=\"text-gray-600 mt-2\">Generated on: <span class=\"font-mono\">{_html_escape(now_de)}</span> (Europe/Berlin)</p>
            <div class=\"mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4\">
                <div class=\"p-4 rounded-lg bg-blue-50\">
                    <div class=\"text-sm text-blue-700\">Late checklist items</div>
                    <div class=\"text-2xl font-bold text-blue-900\">{total_late}</div>
                </div>
                <div class=\"p-4 rounded-lg bg-indigo-50\">
                    <div class=\"text-sm text-indigo-700\">Late projects</div>
                    <div class=\"text-2xl font-bold text-indigo-900\">{total_late_projects}</div>
                </div>
                <div class=\"p-4 rounded-lg bg-gray-50\">
                    <div class=\"text-sm text-gray-700\">Data source</div>
                    <div class=\"text-sm font-mono text-gray-900\">SQLite (db_parallel)</div>
                </div>
            </div>
        </div>

        <div class=\"bg-white rounded-lg shadow overflow-hidden mb-8\">
            <div class=\"px-6 py-4 border-b\">
                <h2 class=\"text-xl font-semibold\">Late projects (by actor)</h2>
                <p class=\"text-gray-600 text-sm mt-1\">Each row represents a late checklist item (actor task) on a card.</p>
            </div>
            <div class=\"overflow-x-auto\">
                <table class=\"min-w-full\">
                    <thead class=\"bg-gray-100\">
                        <tr>
                            <th class=\"px-4 py-3 text-left text-sm font-semibold text-gray-700\">Project</th>
                            <th class=\"px-4 py-3 text-left text-sm font-semibold text-gray-700\">Actor</th>
                            <th class=\"px-4 py-3 text-left text-sm font-semibold text-gray-700\">List</th>
                            <th class=\"px-4 py-3 text-left text-sm font-semibold text-gray-700\">Due (UTC)</th>
                            <th class=\"px-4 py-3 text-left text-sm font-semibold text-gray-700\">Late</th>
                            <th class=\"px-4 py-3 text-left text-sm font-semibold text-gray-700\">Link</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(project_rows) if project_rows else '<tr><td class="px-4 py-6 text-gray-600" colspan="6">No late items detected.</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>

        <div class=\"bg-white rounded-lg shadow overflow-hidden\">
            <div class=\"px-6 py-4 border-b\">
                <h2 class=\"text-xl font-semibold\">Late actors overview</h2>
                <p class=\"text-gray-600 text-sm mt-1\">Count of late checklist items per actor for the latest run.</p>
            </div>
            <div class=\"overflow-x-auto\">
                <table class=\"min-w-full\">
                    <thead class=\"bg-gray-100\">
                        <tr>
                            <th class=\"px-4 py-3 text-left text-sm font-semibold text-gray-700\">Actor</th>
                            <th class=\"px-4 py-3 text-left text-sm font-semibold text-gray-700\">Late items</th>
                            <th class=\"px-4 py-3 text-left text-sm font-semibold text-gray-700\">Worst lateness</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(actor_rows) if actor_rows else '<tr><td class="px-4 py-6 text-gray-600" colspan="3">No late actors detected.</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>

        <div class=\"text-xs text-gray-500 mt-8 mb-10\">
            <p>Rule: a checklist item is late if its state is not complete and current time in Europe/Berlin is after the card due date.</p>
            <p>Note: due dates are stored in UTC (Trello format) and compared using Europe/Berlin time (CET/CEST-safe).</p>
        </div>
    </div>
</body>
</html>
"""

        out_path.write_text(html, encoding="utf-8")
        return str(out_path)
    finally:
        conn.close()


def main() -> None:
    out = generate_late_report_from_db()
    print(f"Late report (DB) generated: {out}")


if __name__ == "__main__":
    main()
