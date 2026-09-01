from __future__ import annotations

from pathlib import Path

import pytest

from enhanced_second_brain.benchmark import run
from enhanced_second_brain.cli import main
from enhanced_second_brain.config import resolve_settings
from enhanced_second_brain.installer import (
    _agent_command,
    install,
    write_agent_instructions,
)
from enhanced_second_brain.okf import audit_vault
from enhanced_second_brain.service import cite, read_page, search, upsert_page
from enhanced_second_brain.usage import aggregate


def test_empty_init_and_search_read_citation_flow(tmp_path: Path) -> None:
    vault = tmp_path / "brain"
    assert main(["--vault", str(vault), "init"]) == 0
    settings = resolve_settings(vault)
    created = upsert_page(
        settings,
        "concepts/orbit.md",
        title="Orbit notebook",
        description="Fictional orbital observations.",
        body="# Orbit notebook\n\nTracks a fictional comet.",
        tags=["astronomy"],
    )
    assert created["created"]
    assert search(settings, "fictional comet")[0]["path"] == "concepts/orbit.md"
    assert read_page(settings, "concepts/orbit.md")["body"].startswith("# Orbit")
    cite(settings, "concepts/orbit.md")
    usage = aggregate(settings)["concepts/orbit.md"]
    assert usage["effective_usage"] == 3.25
    assert audit_vault(vault, strict=True)["valid"]


def test_demo_benchmark() -> None:
    root = Path(__file__).parents[1]
    vault = root / "examples" / "demo-vault"
    report = run(
        resolve_settings(vault), vault / "benchmark.json", top_k=5, max_p95_ms=2000
    )
    assert report["passed"]
    assert report["recall"] == 1.0


def test_one_command_install_adopts_legacy_markdown(tmp_path: Path) -> None:
    vault = tmp_path / "adopted"
    page = vault / "concepts" / "legacy.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "---\ntitle: Legacy\ntags: [portable]\n---\n\n# Legacy\n\nExisting notes survive migration.\n",
        encoding="utf-8",
    )
    result = install(
        vault,
        automation=True,
        dry_run_automation=True,
    )
    assert result["passed"]
    assert result["preflight_backup"]
    assert (Path(result["preflight_backup"]) / "concepts" / "legacy.md").exists()
    assert (vault / "AGENTS.md").exists()
    assert " --vault " in (vault / "AGENTS.md").read_text(encoding="utf-8")
    assert "`esb " not in (vault / "AGENTS.md").read_text(encoding="utf-8")
    assert result["agent_instructions"]["files"] == ["AGENTS.md"]
    assert result["automation"]["installed"] is False
    assert result["index"]["added"] == 1
    assert audit_vault(vault, strict=True)["valid"]
    second = install(vault, automation=False)
    assert second["migration"]["count"] == 0
    assert second["agent_instructions"]["changed"] == []
    assert main(["--vault", str(vault), "prune", "apply", "--all-candidates"]) == 0


def test_reconcile_adopts_new_plain_markdown(tmp_path: Path) -> None:
    vault = tmp_path / "brain"
    assert main(["--vault", str(vault), "init"]) == 0
    raw = vault / "concepts" / "fresh.md"
    raw.write_text(
        "# Fresh note\n\nNew plain Markdown is normalized automatically.\n",
        encoding="utf-8",
    )
    assert main(["--vault", str(vault), "reconcile"]) == 0
    assert audit_vault(vault, strict=True)["valid"]


def test_page_tools_reject_operational_and_outside_paths(tmp_path: Path) -> None:
    vault = tmp_path / "brain"
    assert main(["--vault", str(vault), "init"]) == 0
    settings = resolve_settings(vault)
    operational = vault / "AGENTS.md"
    operational.write_text("local instructions", encoding="utf-8")
    with pytest.raises(ValueError, match="knowledge Markdown"):
        read_page(settings, "AGENTS.md")
    with pytest.raises(ValueError, match="knowledge Markdown"):
        upsert_page(
            settings,
            "_meta/hidden.md",
            title="Hidden",
            description="Not a knowledge path",
            body="# Hidden",
        )
    with pytest.raises(ValueError, match="knowledge Markdown"):
        upsert_page(
            settings,
            ".hidden.md",
            title="Hidden",
            description="Root dotfiles are operational",
            body="# Hidden",
        )


def test_agent_commands_are_shell_safe() -> None:
    windows = _agent_command(
        Path(r"C:\Knowledge Base"), r"C:\Tools\Enhanced Brain\esb.exe", windows=True
    )
    assert windows == (
        "& 'C:\\Tools\\Enhanced Brain\\esb.exe' --vault 'C:\\Knowledge Base'"
    )
    posix = _agent_command(
        "/home/example/knowledge base", "/opt/enhanced brain/esb", windows=False
    )
    assert posix == ("'/opt/enhanced brain/esb' --vault '/home/example/knowledge base'")


def test_standard_install_connects_without_plugins(tmp_path: Path) -> None:
    vault = tmp_path / "brain"
    result = write_agent_instructions(vault)
    assert result["changed"]
    assert (vault / "AGENTS.md").exists()
