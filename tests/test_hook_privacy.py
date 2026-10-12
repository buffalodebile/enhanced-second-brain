from __future__ import annotations

import json
import zipfile

from enhanced_second_brain import checkpoints, hooks
from enhanced_second_brain.bundle import export_bundle
from enhanced_second_brain.config import Settings
from enhanced_second_brain.installer import install


def test_prompts_and_transcripts_never_persist_and_journals_are_not_exported(tmp_path, monkeypatch):
    vault = tmp_path / "brain"
    install(vault, hooks=False)
    settings = Settings(vault=vault, config_file=None)
    monkeypatch.setattr(hooks, "prepare", lambda *_: {"context": [], "maintenance": {}})
    monkeypatch.setattr("enhanced_second_brain.automation._executable", lambda: "/tools/esb")
    text = "PRIVATE CONVERSATION MUST NOT BE STORED"
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("PRIVATE RAW TRANSCRIPT", encoding="utf-8")
    result = hooks.run(settings, "claude", {"session_id": "private-session", "hook_event_name": "UserPromptSubmit",
                       "transcript_path": str(transcript), "prompt": text})
    token = result["hookSpecificOutput"]["additionalContext"].split("capture turn: ", 1)[1].split(".", 1)[0]
    checkpoints.complete(settings, token, {"updates": []})
    for path in checkpoints.cache_root(settings).rglob("*.json"):
        value = path.read_text(encoding="utf-8")
        assert text not in value and "PRIVATE RAW TRANSCRIPT" not in value
        assert str(transcript) not in value
    destination = tmp_path / "portable.zip"
    export_bundle(settings, destination)
    with zipfile.ZipFile(destination) as archive:
        assert not any("cache/hooks" in path for path in archive.namelist())


def test_claude_identical_prompts_at_distinct_positions_are_distinct_turns(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(hooks, "prepare", lambda *_: {"context": [], "maintenance": {}})
    monkeypatch.setattr("enhanced_second_brain.automation._executable", lambda: "/tools/esb")
    transcript = tmp_path / "session.jsonl"
    transcript.write_text("first", encoding="utf-8")
    event = {"session_id": "session", "hook_event_name": "UserPromptSubmit", "prompt": "same",
             "transcript_path": str(transcript)}
    first = hooks.run(settings, "claude", event)
    repeated = hooks.run(settings, "claude", event)
    def token(result):
        return result["hookSpecificOutput"]["additionalContext"].split("capture turn: ", 1)[1].split(".", 1)[0]
    assert token(repeated) == token(first)
    transcript.write_text("a later position", encoding="utf-8")
    second = hooks.run(settings, "claude", event)
    assert first != second
