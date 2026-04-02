"""Tests for casting decision report logic."""

from datetime import datetime
from pathlib import Path
import sys

import pytz

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generate_casting_report import (
    build_recommendations,
    get_availability,
    parse_trello_datetime,
    rank_speakers,
)


def test_get_availability_expected_case() -> None:
    """Availability should map available and unavailable lists correctly."""
    cards_by_list = {
        "Verfügbare Sprecher:innen": [{"name": "Lucas"}, {"name": "Chaos"}],
        "Nicht verfügbare Sprecher:innen": [{"name": "Drystan"}],
    }

    result = get_availability(cards_by_list)

    assert result["Lucas"] == "available"
    assert result["Chaos"] == "available"
    assert result["Drystan"] == "unavailable"


def test_rank_speakers_edge_case_unavailable_filtered() -> None:
    """Unavailable speakers must not appear in ranking output."""
    stats = {
        "Lucas": {"recent_jobs": 0, "active_jobs": 0, "last_job_at": None},
        "Holger": {"recent_jobs": 0, "active_jobs": 0, "last_job_at": None},
    }
    availability = {"Lucas": "available", "Holger": "unavailable"}

    ranked = rank_speakers(["Lucas", "Holger"], stats, availability)

    assert ranked == ["Lucas"]


def test_parse_trello_datetime_failure_case_invalid_string() -> None:
    """Invalid datetime strings should return None instead of raising."""
    assert parse_trello_datetime("not-a-date") is None


def test_build_recommendations_expected_structure() -> None:
    """Recommendation output should contain required role keys and primaries."""
    now = datetime.now(pytz.UTC).isoformat()
    stats = {
        "Lucas": {"recent_jobs": 0, "active_jobs": 0, "last_job_at": now},
        "Holger": {"recent_jobs": 2, "active_jobs": 1, "last_job_at": now},
        "Chaos": {"recent_jobs": 1, "active_jobs": 0, "last_job_at": now},
        "Sira": {"recent_jobs": 2, "active_jobs": 0, "last_job_at": now},
        "Jade": {"recent_jobs": 3, "active_jobs": 1, "last_job_at": now},
        "Marcel": {"recent_jobs": 2, "active_jobs": 0, "last_job_at": now},
        "Martin": {"recent_jobs": 1, "active_jobs": 0, "last_job_at": now},
        "Nils": {"recent_jobs": 1, "active_jobs": 0, "last_job_at": now},
        "Drystan": {"recent_jobs": 4, "active_jobs": 1, "last_job_at": now},
    }
    availability = {name: "available" for name in stats}

    result = build_recommendations(stats, availability)

    assert "narrator" in result
    assert "female" in result
    assert "male" in result
    assert result["narrator"]["primary"] is not None
    assert result["male"]["civis_taeter"]["primary"] is not None
    assert result["male"]["cops_beamte"]["primary"] is not None
