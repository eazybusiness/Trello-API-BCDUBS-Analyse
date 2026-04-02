"""Generate casting decision reports from Trello data.

This script helps with fair speaker assignment by showing who had fewer jobs
recently, while respecting role fit and availability from Trello lists.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pytz

from trello_client import TrelloClient


@dataclass(frozen=True)
class SpeakerProfile:
    """Speaker metadata used for matching and role fit.

    Args:
        aliases (Set[str]): Valid aliases/usernames to map Trello members.
        fit_notes (str): Role fit note shown in report.
    """

    aliases: Set[str]
    fit_notes: str


SPEAKERS: Dict[str, SpeakerProfile] = {
    "Lucas": SpeakerProfile({"lucas", "luckitoasti", "luckijacobs", "luckijacobs@live.de"}, "Narrator Standard."),
    "Holger": SpeakerProfile({"holger", "einostler", "holger irrmisch"}, "Old male voice, good for older civs/perps."),
    "Chaos": SpeakerProfile({"chaos", "7ady.chaos", "jessica nett", "jessicanett4", "jessica"}, "Wide pitch range, emotional."),
    "Sira": SpeakerProfile({"sira", "siramatasashi", "siraverda"}, "Young sounding, less voice variation."),
    "Jade": SpeakerProfile({"jade", "mommyjade", "jade hagemann"}, "Deeper older tone, emotional."),
    "Marcel": SpeakerProfile({"marcel", "speedfreack", "marcel_speedfreack"}, "Deep, young, emotional, good for perps."),
    "Martin": SpeakerProfile({"martin", "b1gfl4sh", "martinlindner95", "martin lindner"}, "Deep young voice, strong cop fit."),
    "Nils": SpeakerProfile({"nils", "justanothernils", "nilssonnenberg1", "nils sonnenberg"}, "Young deep voice, calmer style."),
    "Drystan": SpeakerProfile({"drystan", "nichtdrystan", "noltedrystan", "drystan dominikus nolte"}, "Young male voice, teen fit."),
}

NARRATOR_POOL = ["Lucas", "Holger"]
FEMALE_POOL = ["Chaos", "Sira", "Jade"]
MALE_POOL = ["Marcel", "Holger", "Martin", "Nils", "Drystan"]


def normalize_text(value: str) -> str:
    """Normalize text for matching.

    Args:
        value (str): Raw input string.

    Returns:
        str: Lowercased and stripped value.
    """

    return (value or "").strip().lower()


def parse_trello_datetime(value: str) -> Optional[datetime]:
    """Parse Trello ISO datetime value.

    Args:
        value (str): Trello datetime string.

    Returns:
        Optional[datetime]: Parsed datetime or None.
    """

    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_json_data(path: str) -> Dict:
    """Load Trello data from local JSON file.

    Args:
        path (str): Input JSON path.

    Returns:
        Dict: Trello data payload.
    """

    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def fetch_trello_data(board_name: str) -> Dict:
    """Load Trello data via API.

    Args:
        board_name (str): Trello board name.

    Returns:
        Dict: Trello data payload.
    """

    client = TrelloClient()
    return client.get_board_cards_with_lists(board_name)


def match_member_to_speaker(member: Dict) -> Optional[str]:
    """Match a Trello member object to canonical speaker name.

    Args:
        member (Dict): Trello member payload.

    Returns:
        Optional[str]: Canonical speaker name if matched.
    """

    username = normalize_text(member.get("username", ""))
    full_name = normalize_text(member.get("fullName", ""))
    first_name = normalize_text(full_name.split(" ")[0] if full_name else "")

    for speaker, profile in SPEAKERS.items():
        if username in profile.aliases:
            return speaker
        if first_name in profile.aliases:
            return speaker
        if any(alias in full_name for alias in profile.aliases):
            return speaker
    return None


def get_availability(cards_by_list: Dict[str, List[Dict]]) -> Dict[str, str]:
    """Extract availability from Trello availability lists.

    Args:
        cards_by_list (Dict[str, List[Dict]]): Trello cards grouped by list.

    Returns:
        Dict[str, str]: availability per speaker: available/unavailable/unknown.
    """

    availability = {name: "unknown" for name in SPEAKERS}

    for card in cards_by_list.get("Verfügbare Sprecher:innen", []):
        name = card.get("name", "")
        if name in availability:
            availability[name] = "available"

    for card in cards_by_list.get("Nicht verfügbare Sprecher:innen", []):
        name = card.get("name", "")
        if name in availability:
            availability[name] = "unavailable"

    return availability


def build_stats(cards_by_list: Dict[str, List[Dict]], window_days: int) -> Dict[str, Dict]:
    """Build workload statistics per speaker.

    Args:
        cards_by_list (Dict[str, List[Dict]]): Trello cards grouped by list.
        window_days (int): Lookback window for recent jobs.

    Returns:
        Dict[str, Dict]: Speaker stats used for ranking and report display.
    """

    stats = {
        speaker: {
            "recent_jobs": 0,
            "active_jobs": 0,
            "last_job_at": None,
        }
        for speaker in SPEAKERS
    }

    cutoff = datetime.now(pytz.UTC) - timedelta(days=window_days)
    ignored_lists = {"Verfügbare Sprecher:innen", "Nicht verfügbare Sprecher:innen"}

    for list_name, cards in cards_by_list.items():
        if list_name in ignored_lists:
            continue

        for card in cards:
            members = card.get("members", [])
            if not members:
                continue

            card_dt = parse_trello_datetime(card.get("due") or card.get("dateLastActivity") or "")
            is_recent = card_dt is not None and card_dt >= cutoff
            is_active = list_name == "Skripte zur Aufnahme"

            matched = {m for m in (match_member_to_speaker(member) for member in members) if m}
            for speaker in matched:
                if is_recent:
                    stats[speaker]["recent_jobs"] += 1
                if is_active:
                    stats[speaker]["active_jobs"] += 1
                if card_dt is not None:
                    current = parse_trello_datetime(stats[speaker]["last_job_at"] or "")
                    if current is None or card_dt > current:
                        stats[speaker]["last_job_at"] = card_dt.isoformat()

    return stats


def rank_speakers(
    pool: List[str],
    stats: Dict[str, Dict],
    availability: Dict[str, str],
    bias: Optional[Dict[str, float]] = None,
) -> List[str]:
    """Rank candidates by fairness score (lower means should be considered first).

    Args:
        pool (List[str]): Candidate speakers for a role.
        stats (Dict[str, Dict]): Workload metrics.
        availability (Dict[str, str]): Availability status.
        bias (Optional[Dict[str, float]]): Manual role-fit bias.

    Returns:
        List[str]: Ranked speaker names.
    """

    role_bias = bias or {}
    scored: List[Tuple[str, float]] = []
    for speaker in pool:
        if availability.get(speaker) == "unavailable":
            continue
        score = (
            stats[speaker]["recent_jobs"]
            + (stats[speaker]["active_jobs"] * 0.35)
            + role_bias.get(speaker, 0.0)
        )
        scored.append((speaker, score))

    scored.sort(key=lambda item: (item[1], stats[item[0]]["recent_jobs"], item[0]))
    return [name for name, _ in scored]


def build_recommendations(stats: Dict[str, Dict], availability: Dict[str, str]) -> Dict[str, Dict]:
    """Build role-based recommendations.

    Args:
        stats (Dict[str, Dict]): Workload metrics.
        availability (Dict[str, str]): Availability status.

    Returns:
        Dict[str, Dict]: Recommendations for narrator/female/male split roles.
    """

    narrator_ranked = rank_speakers(NARRATOR_POOL, stats, availability, {"Lucas": -0.10})
    female_ranked = rank_speakers(FEMALE_POOL, stats, availability, {"Chaos": -0.05, "Jade": 0.05})
    civis_ranked = rank_speakers(MALE_POOL, stats, availability, {"Holger": -0.15, "Drystan": -0.10, "Marcel": -0.08})
    cops_ranked = rank_speakers(MALE_POOL, stats, availability, {"Martin": -0.25, "Nils": -0.05})

    # Reason: Narrator follows fixed business rule first (Lucas, then Holger),
    # then fairness ordering for alternatives.
    narrator_primary = None
    if availability.get("Lucas") != "unavailable":
        narrator_primary = "Lucas"
    elif availability.get("Holger") != "unavailable":
        narrator_primary = "Holger"

    if narrator_primary:
        narrator_ranked = [narrator_primary] + [speaker for speaker in narrator_ranked if speaker != narrator_primary]

    # Reason: Chaos and Sira are primary female pool, Jade is fallback.
    female_primary_pool = [speaker for speaker in ["Chaos", "Sira"] if availability.get(speaker) != "unavailable"]
    female_primary = None
    if female_primary_pool:
        female_primary = sorted(
            female_primary_pool,
            key=lambda speaker: (
                stats[speaker]["recent_jobs"] + (stats[speaker]["active_jobs"] * 0.35),
                speaker,
            ),
        )[0]
    elif availability.get("Jade") != "unavailable":
        female_primary = "Jade"

    if female_primary:
        female_ranked = [female_primary] + [speaker for speaker in female_ranked if speaker != female_primary]

    civis_primary = civis_ranked[0] if civis_ranked else None
    cops_ranked_no_duplicate = [candidate for candidate in cops_ranked if candidate != civis_primary]
    cops_primary = cops_ranked_no_duplicate[0] if cops_ranked_no_duplicate else None
    if cops_primary is None and cops_ranked:
        cops_primary = cops_ranked[0]

    narrator_unavailable = [speaker for speaker in NARRATOR_POOL if availability.get(speaker) == "unavailable"]
    female_unavailable = [speaker for speaker in FEMALE_POOL if availability.get(speaker) == "unavailable"]
    male_unavailable = [speaker for speaker in MALE_POOL if availability.get(speaker) == "unavailable"]

    return {
        "narrator": {
            "primary": narrator_primary or (narrator_ranked[0] if narrator_ranked else None),
            "ranked": narrator_ranked,
            "unavailable": narrator_unavailable,
        },
        "female": {
            "primary": female_primary or (female_ranked[0] if female_ranked else None),
            "ranked": female_ranked,
            "unavailable": female_unavailable,
        },
        "male": {
            "civis_taeter": {
                "primary": civis_primary,
                "ranked": civis_ranked,
                "unavailable": male_unavailable,
            },
            "cops_beamte": {
                "primary": cops_primary,
                "ranked": cops_ranked_no_duplicate,
                "unavailable": male_unavailable,
            },
        },
    }


def format_date(iso_date: Optional[str]) -> str:
    """Format ISO datetime to DD.MM.YYYY for report.

    Args:
        iso_date (Optional[str]): ISO date value.

    Returns:
        str: Formatted date or '-'.
    """

    dt = parse_trello_datetime(iso_date or "")
    return dt.strftime("%d.%m.%Y") if dt else "-"


def generate_html(
    stats: Dict[str, Dict],
    availability: Dict[str, str],
    recommendations: Dict[str, Dict],
    window_days: int,
    output_file: str,
) -> str:
    """Render HTML casting report.

    Args:
        stats (Dict[str, Dict]): Speaker workload stats.
        availability (Dict[str, str]): Availability map.
        recommendations (Dict[str, Dict]): Ranked role recommendations.
        window_days (int): Lookback window for display.
        output_file (str): Destination HTML path.

    Returns:
        str: Created HTML path.
    """

    now = datetime.now(pytz.timezone("Europe/Berlin"))

    rows = []
    for speaker in sorted(SPEAKERS.keys()):
        status = availability.get(speaker, "unknown")
        label = "✓ Verfügbar" if status == "available" else "✗ Nicht verfügbar" if status == "unavailable" else "? Unbekannt"
        rows.append(
            f"<tr class='hover:bg-gray-50'><td class='px-4 py-3 font-semibold'>{speaker}</td>"
            f"<td class='px-4 py-3'>{label}</td>"
            f"<td class='px-4 py-3'>{stats[speaker]['recent_jobs']}</td>"
            f"<td class='px-4 py-3'>{stats[speaker]['active_jobs']}</td>"
            f"<td class='px-4 py-3'>{format_date(stats[speaker]['last_job_at'])}</td>"
            f"<td class='px-4 py-3 text-sm text-gray-600'>{SPEAKERS[speaker].fit_notes}</td></tr>"
        )

    def role_card(title: str, primary: Optional[str], ranked: List[str], unavailable: List[str]) -> str:
        alternatives_list = [speaker for speaker in ranked if speaker != primary][:3]
        alternatives = ", ".join(alternatives_list) if alternatives_list else "-"
        unavailable_text = ", ".join(unavailable) if unavailable else "-"
        return (
            "<div class='bg-white rounded-lg shadow p-5'>"
            f"<h3 class='text-lg font-bold mb-2'>{title}</h3>"
            f"<p class='text-sm mb-2'>Primär: <span class='font-semibold'>{primary or '-'}</span></p>"
            f"<p class='text-sm text-gray-600'>Alternativen: {alternatives}</p>"
            f"<p class='text-sm text-gray-500 mt-2'>Aktuell nicht verfügbar: {unavailable_text}</p>"
            "</div>"
        )

    html = f"""<!doctype html>
<html lang='de'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width,initial-scale=1'>
  <title>Casting Entscheidungshilfe</title>
  <script src='https://cdn.tailwindcss.com'></script>
</head>
<body class='bg-gray-100 text-gray-900'>
  <main class='max-w-7xl mx-auto px-4 py-8'>
    <header class='bg-gradient-to-r from-indigo-700 to-blue-700 text-white rounded-xl p-6 shadow mb-6'>
      <h1 class='text-3xl font-bold'>Casting Entscheidungshilfe</h1>
      <p class='text-blue-100 mt-2'>Wer hatte zuletzt weniger Jobs + wer passt zur Rolle?</p>
      <p class='text-xs text-blue-200 mt-3'>Timestamp: {now.strftime('%d.%m.%Y %H:%M:%S')} CET</p>
    </header>

    <section class='grid grid-cols-1 md:grid-cols-2 gap-4 mb-6'>
      {role_card('Narrator', recommendations['narrator']['primary'], recommendations['narrator']['ranked'], recommendations['narrator']['unavailable'])}
      {role_card('Weibliche Rollen', recommendations['female']['primary'], recommendations['female']['ranked'], recommendations['female']['unavailable'])}
      {role_card('Männlich: Zivis/Täter', recommendations['male']['civis_taeter']['primary'], recommendations['male']['civis_taeter']['ranked'], recommendations['male']['civis_taeter']['unavailable'])}
      {role_card('Männlich: Cops/Beamte', recommendations['male']['cops_beamte']['primary'], recommendations['male']['cops_beamte']['ranked'], recommendations['male']['cops_beamte']['unavailable'])}
    </section>

    <section class='bg-white rounded-xl shadow overflow-hidden'>
      <div class='px-4 py-3 border-b bg-gray-50'>
        <h2 class='text-xl font-bold'>Übersicht nach Fairness ({window_days} Tage Fenster)</h2>
      </div>
      <div class='overflow-x-auto'>
        <table class='w-full text-sm'>
          <thead class='bg-gray-100 text-gray-700'>
            <tr>
              <th class='px-4 py-3 text-left'>Sprecher</th>
              <th class='px-4 py-3 text-left'>Verfügbarkeit</th>
              <th class='px-4 py-3 text-left'>Jobs (letzte {window_days} Tage)</th>
              <th class='px-4 py-3 text-left'>Aktive Jobs</th>
              <th class='px-4 py-3 text-left'>Letzter Job</th>
              <th class='px-4 py-3 text-left'>Passung</th>
            </tr>
          </thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
    </section>
  </main>
</body>
</html>
"""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return str(output_path)


def write_json_output(payload: Dict, output_file: str) -> str:
    """Write JSON report payload.

    Args:
        payload (Dict): Payload to serialize.
        output_file (str): Destination file path.

    Returns:
        str: Created JSON path.
    """

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(output_path)


def main() -> None:
    """Program entrypoint.

    Args:
        None

    Returns:
        None
    """

    parser = argparse.ArgumentParser(description="Generate casting report for speaker assignment decisions.")
    parser.add_argument("--source", choices=["json", "trello"], default="json")
    parser.add_argument("--json-input", default="trello_cards_detailed.json")
    parser.add_argument("--board-name", default="True Crime Video Dubs")
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--html-output", default="reports/casting_decision_report.html")
    parser.add_argument("--json-output", default="reports/casting_decision_report.json")
    args = parser.parse_args()

    if args.source == "trello":
        data = fetch_trello_data(args.board_name)
        Path(args.json_input).write_text(json.dumps(data, indent=2), encoding="utf-8")
    else:
        data = load_json_data(args.json_input)

    cards_by_list = data.get("cards_by_list", {})
    availability = get_availability(cards_by_list)
    stats = build_stats(cards_by_list, args.days)
    recommendations = build_recommendations(stats, availability)

    html_path = generate_html(stats, availability, recommendations, args.days, args.html_output)
    json_payload = {
        "generated_at": datetime.now(pytz.timezone("Europe/Berlin")).isoformat(),
        "window_days": args.days,
        "availability": availability,
        "recommendations": recommendations,
        "speakers": stats,
    }
    json_path = write_json_output(json_payload, args.json_output)

    print(f"Casting HTML report generated: {html_path}")
    print(f"Casting JSON report generated: {json_path}")


if __name__ == "__main__":
    main()
