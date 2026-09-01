from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest
from conftest import write_page

from enhanced_second_brain.bundle import (
    BUNDLE_FORMAT,
    BUNDLE_VERSION,
    MANIFEST_NAME,
    _safe_member,
    export_bundle,
    restore_bundle,
)
from enhanced_second_brain.config import DEFAULT_TOML, Settings
from enhanced_second_brain.errors import SafetyError, ValidationError


def test_portable_bundle_round_trip_keeps_context_not_machine_state(
    tmp_path: Path, vault: Path, settings: Settings
) -> None:
    (vault / "second-brain.toml").write_text(DEFAULT_TOML, encoding="utf-8")
    write_page(
        vault,
        "concepts/portable.md",
        title="Portable context",
        description="Knowledge survives the machine.",
        body="# Portable context\n\nRelative links and UTF-8 café survive.",
    )
    archive = vault / "_archives" / "pruned" / "2026-08-01" / "old.md"
    archive.parent.mkdir(parents=True)
    archive.write_text("# Archived context\n", encoding="utf-8")
    attachment = vault / "references" / "diagram.bin"
    attachment.parent.mkdir(parents=True)
    attachment.write_bytes(b"portable-attachment")
    usage = vault / "_meta" / "usage.jsonl"
    usage.parent.mkdir(parents=True)
    usage.write_text('{"event":"opened","path":"concepts/portable.md"}\n')
    cache = vault / "_meta" / "cache" / "esb-fts.sqlite3"
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b"disposable")
    (vault / "AGENTS.md").write_text("machine-specific", encoding="utf-8")
    (vault / ".gitignore").write_text("_meta/cache/\n", encoding="utf-8")

    output = tmp_path / "copies" / "brain.zip"
    result = export_bundle(settings, output)
    assert result["verified"] is True
    assert result["sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()

    with zipfile.ZipFile(output) as bundle:
        names = set(bundle.namelist())
        assert "concepts/portable.md" in names
        assert "_archives/pruned/2026-08-01/old.md" in names
        assert "references/diagram.bin" in names
        assert "_meta/usage.jsonl" in names
        assert "_meta/cache/esb-fts.sqlite3" not in names
        assert "AGENTS.md" not in names
        assert ".gitignore" not in names
        manifest = json.loads(bundle.read(MANIFEST_NAME))
        assert manifest["format"] == BUNDLE_FORMAT
        assert manifest["format_version"] == BUNDLE_VERSION
        assert all(not Path(item["path"]).is_absolute() for item in manifest["files"])

    restored = tmp_path / "restored"
    restored_result = restore_bundle(output, restored)
    assert restored_result["verified"] is True
    assert (
        (restored / "concepts" / "portable.md")
        .read_text(encoding="utf-8")
        .endswith("UTF-8 café survive.\n")
    )
    assert (restored / "_meta" / "usage.jsonl").exists()
    assert (restored / "_meta" / "cache" / "esb-fts.sqlite3").exists()
    assert not (restored / "AGENTS.md").exists()
    assert restored_result["audit"]["valid"] is True


def test_export_refuses_secret_like_files_and_destinations_inside_vault(
    tmp_path: Path, vault: Path, settings: Settings
) -> None:
    write_page(
        vault,
        "concepts/safe.md",
        title="Safe",
        description="Safe knowledge.",
        body="# Safe",
    )
    with pytest.raises(SafetyError, match="outside the vault"):
        export_bundle(settings, vault / "export.zip")
    (vault / ".env").write_text("TOKEN=not-a-real-token", encoding="utf-8")
    with pytest.raises(SafetyError, match="secret-like filename"):
        export_bundle(settings, tmp_path / "export.zip")


def test_restore_rejects_checksum_changes_and_existing_destination(
    tmp_path: Path,
) -> None:
    content = b"changed"
    manifest = {
        "format": BUNDLE_FORMAT,
        "format_version": BUNDLE_VERSION,
        "files": [
            {
                "path": "concepts/note.md",
                "size": len(content),
                "sha256": "0" * 64,
            }
        ],
    }
    bundle = tmp_path / "tampered.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr(MANIFEST_NAME, json.dumps(manifest))
        archive.writestr("concepts/note.md", content)
    with pytest.raises(ValidationError, match="checksum mismatch"):
        restore_bundle(bundle, tmp_path / "new-vault")

    destination = tmp_path / "existing"
    destination.mkdir()
    with pytest.raises(SafetyError, match="must not exist"):
        restore_bundle(bundle, destination)


def test_restore_rejects_path_traversal(tmp_path: Path) -> None:
    content = b"escape"
    manifest = {
        "format": BUNDLE_FORMAT,
        "format_version": BUNDLE_VERSION,
        "files": [
            {
                "path": "../escape.md",
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        ],
    }
    bundle = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr(MANIFEST_NAME, json.dumps(manifest))
        archive.writestr("../escape.md", content)
    with pytest.raises(SafetyError, match="Unsafe bundle path"):
        restore_bundle(bundle, tmp_path / "restored")
    assert not (tmp_path / "escape.md").exists()


@pytest.mark.parametrize("path", ["CON.md", "concepts/bad:name.md", "note. "])
def test_bundle_rejects_paths_that_are_not_cross_platform(path: str) -> None:
    with pytest.raises(SafetyError, match="portable bundle path"):
        _safe_member(path)
