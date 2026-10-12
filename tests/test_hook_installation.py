from __future__ import annotations

import json
from pathlib import Path

import pytest

from enhanced_second_brain import hook_installation as native
from enhanced_second_brain.installer import install


@pytest.mark.parametrize("provider", ["codex", "claude"])
def test_install_upgrade_and_uninstall_preserve_existing_hooks(settings, monkeypatch, provider):
    monkeypatch.setattr(native, "_executable", lambda: "/tools/Brain's $app/esb")
    path = native._config(provider)
    path.parent.mkdir(parents=True)
    existing = {"unrelated": True, "hooks": {"Stop": [{"matcher": "custom", "hooks": [
        {"type": "command", "command": "user-check"}]}], "PreToolUse": [{"hooks": []}]}}
    path.write_text(json.dumps(existing), encoding="utf-8")
    assert native.configure(settings, provider)["changed"] == [provider]
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["hooks"]["Stop"][0] == existing["hooks"]["Stop"][0]
    assert data["unrelated"] is True
    assert native.configure(settings, provider)["changed"] == []
    monkeypatch.setattr(native, "_executable", lambda: "/new/esb")
    assert native.configure(settings, provider)["changed"] == [provider]
    assert native.status(settings, provider)["providers"][provider]["configured"]
    assert native.configure(settings, provider, uninstall=True)["changed"] == [provider]
    assert json.loads(path.read_text(encoding="utf-8")) == existing
    assert native.configure(settings, provider, uninstall=True)["changed"] == []


def test_two_vaults_do_not_remove_each_others_configuration(settings, tmp_path, monkeypatch):
    from enhanced_second_brain.config import Settings
    monkeypatch.setattr(native, "_executable", lambda: "/tools/esb")
    other = Settings(vault=tmp_path / "other vault", config_file=None)
    native.configure(settings, "claude")
    native.configure(other, "claude")
    native.configure(settings, "claude", uninstall=True)
    assert native.status(other, "claude")["providers"]["claude"]["configured"]


def test_claude_exec_form_has_no_shell_interpolation(settings, monkeypatch):
    monkeypatch.setattr(native, "_executable", lambda: "C:/Apps/O'Brien $tools/esb.exe")
    handler = native._handler(settings, "claude", "synthetic-id")
    assert handler["command"] == "C:/Apps/O'Brien $tools/esb.exe"
    assert handler["args"][1] == str(settings.vault)
    assert "shell" not in handler


def test_codex_requires_native_review_and_malformed_config_is_preserved(settings, monkeypatch):
    monkeypatch.setattr(native, "_executable", lambda: "/tools/esb")
    native.configure(settings, "codex")
    assert native.status(settings)["providers"]["codex"]["activation"] == "native_review_required"
    path = native._config("codex")
    content = '{"hooks": []}'
    path.write_text(content, encoding="utf-8")
    assert native.configure(settings, "codex")["errors"]
    assert path.read_text(encoding="utf-8") == content


def test_install_opt_out_does_not_touch_provider_configs(tmp_path, monkeypatch):
    monkeypatch.setattr(native, "configure", lambda *_: pytest.fail("Hooks explicitly disabled"))
    result = install(tmp_path / "brain", hooks=False)
    assert result["hooks"] == {"installed": False, "reason": "disabled"}
