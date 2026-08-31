from __future__ import annotations

from pathlib import Path

import pytest

from enhanced_second_brain.config import Settings
from enhanced_second_brain.pages import dump_markdown


def write_page(
    vault: Path,
    relative: str,
    *,
    title: str,
    description: str,
    body: str,
    tags: list[str] | None = None,
    relationships: list[dict[str, str]] | None = None,
    tier: str = "supporting",
    lifecycle: str = "stable",
    status: str | None = None,
    updated: str = "2026-01-01T00:00:00+00:00",
    confidential: bool = False,
) -> Path:
    metadata = {
        "type": "Concept",
        "title": title,
        "description": description,
        "tags": tags or [],
        "sources": [{"resource": "urn:fiction:test"}],
        "generated": {"by": "process:test", "at": updated},
        "status": status or lifecycle,
        "summary": description,
        "category": "concepts",
        "relationships": relationships or [],
        "base_confidence": 0.8,
        "lifecycle": lifecycle,
        "tier": tier,
        "created": updated,
        "updated": updated,
    }
    if confidential:
        metadata["confidential"] = True
    path = vault / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_markdown(metadata, body), encoding="utf-8", newline="\n")
    return path


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    root.mkdir()
    return root


@pytest.fixture
def settings(vault: Path) -> Settings:
    return Settings(vault=vault, config_file=None)
