from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime

import pytest
from conftest import write_page

from enhanced_second_brain.config import ArchiveConfig, Settings
from enhanced_second_brain.errors import SafetyError, ValidationError
from enhanced_second_brain.prune import apply, candidates, restore
from enhanced_second_brain.usage import aggregate, events, record


def test_weighted_usage_is_locked_and_concurrent(settings, vault) -> None:
    write_page(
        vault, "concepts/used.md", title="Used", description="Used page", body="# Used"
    )
    tasks = [("injected", 12), ("opened", 5), ("cited", 3)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [
            pool.submit(record, settings, event, "concepts/used.md")
            for event, count in tasks
            for _ in range(count)
        ]
        for future in futures:
            future.result()
    assert len(events(vault)) == 20
    assert aggregate(settings)["concepts/used.md"]["effective_usage"] == 14.0
    assert aggregate(settings)["concepts/used.md"]["decayed_effective_usage"] > 13.9


def test_prune_safeguards_archive_and_restore(vault) -> None:
    old = "2020-01-01T00:00:00+00:00"
    write_page(
        vault,
        "concepts/cold.md",
        title="Cold",
        description="Cold page",
        body="# Cold",
        tier="peripheral",
        updated=old,
    )
    write_page(
        vault,
        "concepts/core.md",
        title="Core",
        description="Core page",
        body="# Core",
        tier="core",
        updated=old,
    )
    write_page(
        vault,
        "concepts/verified.md",
        title="Verified",
        description="Verified page",
        body="# Verified",
        lifecycle="verified",
        tier="peripheral",
        updated=old,
    )
    write_page(
        vault,
        "concepts/status-verified.md",
        title="Status verified",
        description="Protected by official status",
        body="# Status verified",
        lifecycle="stable",
        status="verified",
        tier="peripheral",
        updated=old,
    )
    write_page(
        vault,
        "concepts/status-rejected.md",
        title="Status rejected",
        description="Rejected decisions remain useful history",
        body="# Status rejected",
        lifecycle="stable",
        status="rejected",
        tier="peripheral",
        updated=old,
    )
    write_page(
        vault,
        "concepts/private.md",
        title="Private",
        description="Private page",
        body="# Private",
        confidential=True,
        tier="peripheral",
        updated=old,
    )
    settings = Settings(
        vault=vault, config_file=None, archive=ArchiveConfig(cold_threshold=1.0)
    )
    now = datetime(2026, 8, 31, tzinfo=UTC)
    assert [row["path"] for row in candidates(settings, now=now)] == [
        "concepts/cold.md"
    ]
    with pytest.raises(SafetyError):
        apply(settings, ["concepts/core.md"], archive_date=date(2026, 8, 31))
    moved = apply(settings, ["concepts/cold.md"], archive_date=date(2026, 8, 31))
    archived = moved["moved"][0]["to"]
    assert not (vault / "concepts/cold.md").exists()
    assert (vault / archived).exists()
    assert restore(settings, archived)["to"] == "concepts/cold.md"
    assert (vault / "concepts/cold.md").exists()
    restored = (vault / "concepts/cold.md").read_text(encoding="utf-8")
    assert "lifecycle: stable" in restored
    assert "status: stable" in restored
    assert "archive_previous" not in restored


def test_path_confinement(settings, vault, tmp_path) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")
    with pytest.raises(SafetyError):
        record(settings, "opened", outside)
    operational = vault / "AGENTS.md"
    operational.write_text("not knowledge", encoding="utf-8")
    with pytest.raises(ValidationError, match="knowledge Markdown"):
        record(settings, "opened", operational)
