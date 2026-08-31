from __future__ import annotations

from pathlib import Path

from enhanced_second_brain.config import resolve_settings
from enhanced_second_brain.okf import audit_vault, migrate_vault
from enhanced_second_brain.pages import parse_markdown


def test_config_precedence(tmp_path: Path, monkeypatch) -> None:
    configured = tmp_path / "configured"
    env = tmp_path / "environment"
    cli = tmp_path / "cli"
    for path in (configured, env, cli):
        path.mkdir()
    (tmp_path / "second-brain.toml").write_text(
        '[vault]\npath = "configured"\n', encoding="utf-8"
    )
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert resolve_settings(start=nested).vault == configured
    monkeypatch.setenv("ESB_VAULT_PATH", str(env))
    assert resolve_settings(start=nested).vault == env
    assert resolve_settings(cli, start=nested).vault == cli


def test_explicit_vault_loads_its_own_policy(tmp_path: Path) -> None:
    vault = tmp_path / "target"
    vault.mkdir()
    (vault / "second-brain.toml").write_text(
        '[vault]\npath = "."\n[archive]\ninactive_days = 999\n[mcp]\nallow_writes = true\n',
        encoding="utf-8",
    )
    settings = resolve_settings(vault, start=tmp_path)
    assert settings.config_file == vault / "second-brain.toml"
    assert settings.archive.inactive_days == 999
    assert settings.mcp_allow_writes is True


def test_migration_is_dry_run_idempotent_and_strict(vault: Path) -> None:
    page = vault / "concepts" / "legacy.md"
    page.parent.mkdir()
    page.write_text(
        "---\ntitle: Legacy note\ntags: [café]\n---\n\n# Legacy note\n\nA portable summary.\n",
        encoding="utf-8",
    )
    preview = migrate_vault(vault, write=False)
    assert preview["changed"] == ["concepts/legacy.md"]
    assert "description:" not in page.read_text(encoding="utf-8")
    assert migrate_vault(vault, write=True)["count"] == 1
    assert migrate_vault(vault, write=True)["count"] == 0
    assert audit_vault(vault, strict=True)["valid"]


def test_migration_preserves_bom_frontmatter_and_normalizes_profile(
    vault: Path,
) -> None:
    page = vault / "concepts" / "windows.md"
    page.parent.mkdir()
    page.write_text(
        "\ufeff---\n"
        "title: Windows note\n"
        "description: Old description\n"
        "summary: Canonical summary\n"
        "category: analysis\n"
        "tags: [portable]\n"
        "---\n\n"
        "# Windows note\n\nBody survives intact.\n",
        encoding="utf-8",
    )
    assert migrate_vault(vault, write=True)["count"] == 1
    migrated = parse_markdown(page, vault)
    assert migrated.metadata["title"] == "Windows note"
    assert migrated.metadata["tags"] == ["portable"]
    assert migrated.metadata["type"] == "Analysis"
    assert migrated.metadata["description"] == "Canonical summary"
    assert migrated.metadata["summary"] == "Canonical summary"
    assert migrated.body == "# Windows note\n\nBody survives intact.\n"
    assert audit_vault(vault, strict=True)["valid"]
