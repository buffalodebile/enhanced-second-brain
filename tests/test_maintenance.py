from __future__ import annotations

from datetime import UTC, datetime, timedelta

from conftest import write_page

from enhanced_second_brain.config import (
    ArchiveConfig,
    MaintenanceConfig,
    Settings,
)
from enhanced_second_brain.maintenance import (
    initialize,
    review_archive,
    run_turn,
    status,
)


def test_agent_turn_is_cheap_until_time_or_turn_threshold(vault) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    settings = Settings(
        vault=vault,
        config_file=None,
        maintenance=MaintenanceConfig(
            reconcile_after_hours=24,
            reconcile_after_turns=3,
            archive_review_after_days=30,
        ),
    )
    initialize(settings, now=start)
    first = run_turn(settings, now=start + timedelta(minutes=1))
    second = run_turn(settings, now=start + timedelta(minutes=2))
    assert first["reconcile"] == {"due": False, "ran": False}
    assert second["reconcile"] == {"due": False, "ran": False}
    third = run_turn(settings, now=start + timedelta(minutes=3))
    assert third["reconcile"]["ran"] is True
    assert third["reconcile"]["result"]["passed"] is True
    assert status(settings, now=start + timedelta(minutes=3))[
        "turns_since_reconcile"
    ] == 0


def test_archive_review_requires_agent_selection_and_accepts_none(vault) -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    write_page(
        vault,
        "concepts/cold.md",
        title="Cold",
        description="A deliberately cold page",
        body="# Cold",
        tier="peripheral",
        updated="2020-01-01T00:00:00+00:00",
    )
    settings = Settings(
        vault=vault,
        config_file=None,
        maintenance=MaintenanceConfig(archive_review_after_days=30),
        archive=ArchiveConfig(cold_threshold=1.0),
    )
    initialize(settings, now=start)
    due = run_turn(settings, now=start + timedelta(days=31))
    assert due["archive_review"]["due"] is True
    assert due["archive_review"]["candidates"][0]["path"] == "concepts/cold.md"
    assert (vault / "concepts/cold.md").exists()

    skipped = review_archive(settings, [], now=start + timedelta(days=31))
    assert skipped == {"reviewed": True, "moved": [], "count": 0}
    assert (vault / "concepts/cold.md").exists()
    assert run_turn(settings, now=start + timedelta(days=31, minutes=1))[
        "archive_review"
    ]["due"] is False


def test_agent_can_archive_only_the_semantically_reviewed_candidate(vault) -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    write_page(
        vault,
        "concepts/cold.md",
        title="Cold",
        description="A deliberately cold page",
        body="# Cold",
        tier="peripheral",
        updated="2020-01-01T00:00:00+00:00",
    )
    settings = Settings(
        vault=vault,
        config_file=None,
        archive=ArchiveConfig(cold_threshold=1.0),
    )
    initialize(settings, now=start)
    result = review_archive(
        settings, ["concepts/cold.md"], now=start + timedelta(days=31)
    )
    assert result["reviewed"] is True
    assert result["count"] == 1
    assert not (vault / "concepts/cold.md").exists()
