from pathlib import Path

import pytest

from enhanced_second_brain.bundle import _safe_member
from enhanced_second_brain.errors import SafetyError, ValidationError
from enhanced_second_brain.index import query, rebuild
from enhanced_second_brain.installer import _initialize
from enhanced_second_brain.pages import is_knowledge_path, iter_page_paths
from enhanced_second_brain.service import read_page


def test_machine_local_is_not_indexed_or_read_as_knowledge(vault, settings):
    local = vault / "_local"
    local.mkdir()
    private = local / "notes.md"
    private.write_text("# CanaryPrivateCredential\nsynthetic-only", encoding="utf-8")
    assert not is_knowledge_path(vault, private)
    assert private not in list(iter_page_paths(vault))
    rebuild(settings)
    assert not query(settings, "CanaryPrivateCredential")
    with pytest.raises((SafetyError, ValidationError, ValueError)):
        read_page(settings, "_local/notes.md")


def test_install_adds_private_exclusions_without_overwriting_existing(vault):
    (vault / ".gitignore").write_text("my-local-data/\n")
    _initialize(vault)
    _initialize(vault)
    lines = (vault / ".gitignore").read_text().splitlines()
    assert "my-local-data/" in lines
    assert lines.count("_local/") == 1
    assert ".env" in lines


def test_restore_refuses_machine_local_member():
    with pytest.raises((SafetyError, ValidationError)):
        _safe_member("_local/.env")
