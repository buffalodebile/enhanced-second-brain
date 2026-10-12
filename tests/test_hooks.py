from __future__ import annotations

import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from enhanced_second_brain import checkpoints, hooks, index
from enhanced_second_brain.atomic import read_json
from enhanced_second_brain.cli import main
from enhanced_second_brain.errors import SafetyError, ValidationError
from enhanced_second_brain.service import read_page, upsert_page

from conftest import write_page


@pytest.fixture
def cheap_context(monkeypatch):
    calls = []
    monkeypatch.setattr(hooks, "prepare", lambda settings, prompt: calls.append(prompt) or {"context": [], "maintenance": {}})
    monkeypatch.setattr("enhanced_second_brain.automation._executable", lambda: "/tools/esb")
    return calls


def begin(settings, event_id="event-1", session="session-1", provider="generic"):
    result = hooks.run(settings, provider, {"session_id": session, "event_id": event_id,
                       "event": "begin", "hook_event_name": "UserPromptSubmit", "prompt": "A durable decision"})
    if provider == "generic":
        return result["turn_id"]
    text = result["hookSpecificOutput"]["additionalContext"]
    return text.split("capture turn: ", 1)[1].split(".", 1)[0]


def end(settings, token, provider="generic", **extra):
    return hooks.run(settings, provider, {"session_id": "session-1", "event": "end",
                     "hook_event_name": "Stop", **({"turn_id": token} if provider == "generic" else {}), **extra})


def proposal(path="concepts/decision.md", sha=None, body="# Decision\n\nMeasured result."):
    return {"updates": [{"path": path, "expected_sha256": sha,
            "metadata": {"title": "Decision", "description": "A durable result", "sources": [{"resource": "urn:experiment:new"}]},
            "body": body}]}


@pytest.mark.parametrize("provider", ["generic", "codex", "claude"])
def test_empty_receipt_finishes_without_scanning_or_model(settings, monkeypatch, cheap_context, provider):
    token = begin(settings, provider=provider)
    monkeypatch.setattr(index, "iter_page_paths", lambda *_: pytest.fail("Stop must not scan pages"))
    monkeypatch.setattr(checkpoints, "update_paths", lambda *_: pytest.fail("Empty capture must not open SQLite"))
    assert checkpoints.complete(settings, token, {"updates": []})["complete"]
    result = end(settings, token, provider)
    assert "decision" not in result
    assert result.get("action", "allow") == "allow"
    assert len(cheap_context) == 1


@pytest.mark.parametrize("provider", ["generic", "codex", "claude"])
def test_reminder_is_bounded_and_pending_visible_next_turn(settings, cheap_context, provider):
    token = begin(settings, provider=provider)
    first = end(settings, token, provider)
    assert first.get("decision") == "block" or first.get("action") == "continue"
    second = end(settings, token, provider)
    assert "decision" not in second
    assert "warning" in second or "systemMessage" in second
    third = end(settings, token, provider)
    assert "decision" not in third
    next_turn = hooks.run(settings, provider, {"session_id": "other-session", "event_id": "next",
                           "event": "begin", "hook_event_name": "UserPromptSubmit", "prompt": "Next task"})
    assert token in json.dumps(next_turn)


def test_duplicate_events_and_codex_continuation_do_not_count_again(settings, cheap_context):
    token = begin(settings, provider="codex")
    assert begin(settings, provider="codex") == token
    reminder = end(settings, token, "codex")
    result = hooks.run(settings, "codex", {"session_id": "session-1", "hook_event_name": "UserPromptSubmit",
                       "turn_id": "synthetic-new-turn", "prompt": reminder["reason"]})
    assert token in json.dumps(result)
    assert len(cheap_context) == 1
    assert end(settings, token, "codex", stop_hook_active=True).get("decision") is None


def test_replaying_old_begin_or_stop_does_not_close_new_turn(settings, cheap_context):
    old = begin(settings, event_id="old", provider="codex")
    checkpoints.complete(settings, old, {"updates": []})
    new = begin(settings, event_id="new", provider="codex")
    assert begin(settings, event_id="old", provider="codex") == old
    result = hooks.run(settings, "codex", {"session_id": "session-1", "hook_event_name": "Stop", "turn_id": "old"})
    assert not result
    assert checkpoints.load_turn(settings, new)["reminded"] is False
    assert len(cheap_context) == 2


def test_session_close_and_interruption_preserve_pending(settings, cheap_context):
    token = begin(settings)
    result = hooks.run(settings, "generic", {"session_id": "session-1", "event": "session_end"})
    assert result["action"] == "allow"
    assert checkpoints.load_turn(settings, token)["reminded"] is False
    token2 = begin(settings, event_id="another")
    token3 = begin(settings, event_id="interrupted")
    pending = read_json(checkpoints.cache_root(settings) / "pending.json")
    assert token in pending and token2 in pending and token3 not in pending


def test_batch_preserves_sources_extensions_and_updates_only_touched_pages(settings, cheap_context, monkeypatch):
    path = write_page(settings.vault, "concepts/decision.md", title="Before", description="Prior",
                      body="# Before\n\nPrior decision.", relationships=[{"target": "[[concepts/other]]", "type": "related_to"}])
    token = begin(settings)
    original = read_page(settings, "concepts/decision.md", track=False)
    monkeypatch.setattr(index, "iter_page_paths", lambda *_: pytest.fail("Capture must not walk the vault"))
    payload = proposal(sha=original["sha256"])
    result = checkpoints.complete(settings, token, payload)
    assert result["changed"] == ["concepts/decision.md"]
    updated = read_page(settings, "concepts/decision.md", track=False)
    assert len(updated["metadata"]["sources"]) == 2
    assert updated["metadata"]["relationships"] == original["metadata"]["relationships"]
    assert updated["metadata"]["created"] == original["metadata"]["created"]
    assert updated["metadata"]["generated"]["at"] == updated["metadata"]["updated"]
    assert checkpoints.complete(settings, token, payload)["duplicate"]
    connection = index.connect(settings.vault)
    assert connection.execute("SELECT title FROM pages").fetchone()[0] == "Decision"
    connection.close()


def test_same_content_preserves_bytes_and_timestamps(settings, cheap_context):
    token = begin(settings)
    checkpoints.complete(settings, token, proposal())
    snapshot = read_page(settings, "concepts/decision.md", track=False)
    path = settings.vault / "concepts/decision.md"
    before = path.stat().st_mtime_ns
    next_token = begin(settings, event_id="second")
    result = checkpoints.complete(settings, next_token, {"updates": [{"path": snapshot["path"],
               "expected_sha256": snapshot["sha256"], "metadata": snapshot["metadata"], "body": snapshot["body"]}]})
    assert result["changed"] == []
    assert path.stat().st_mtime_ns == before
    assert path.read_bytes() and read_page(settings, snapshot["path"], track=False)["sha256"] == snapshot["sha256"]


def test_invalid_second_page_prevents_all_writes(settings, cheap_context):
    token = begin(settings)
    payload = proposal()
    payload["updates"].append({"path": "concepts/broken.md", "expected_sha256": None, "metadata": {}, "body": "# Bad"})
    with pytest.raises(ValidationError):
        checkpoints.complete(settings, token, payload)
    assert not (settings.vault / "concepts/decision.md").exists()


def test_concurrent_sessions_cannot_overwrite_one_page(settings, cheap_context):
    token1 = begin(settings)
    token2 = begin(settings, session="session-2")
    def capture(token):
        try:
            return checkpoints.complete(settings, token, proposal())
        except SafetyError:
            return "conflict"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(capture, [token1, token2]))
    assert results.count("conflict") == 1
    assert sum(isinstance(result, dict) for result in results) == 1


def test_retry_after_partial_write_or_index_failure_is_idempotent(settings, cheap_context, monkeypatch):
    token = begin(settings)
    payload = proposal()
    payload["updates"].extend(proposal("concepts/second.md")["updates"])
    original_write = checkpoints.write_text
    calls = []
    def fail_second(path, text):
        calls.append(path)
        if len(calls) == 2:
            raise OSError("Simulated interruption")
        original_write(path, text)
    monkeypatch.setattr(checkpoints, "write_text", fail_second)
    with pytest.raises(OSError):
        checkpoints.complete(settings, token, payload)
    first_bytes = (settings.vault / "concepts/decision.md").read_bytes()
    with pytest.raises(ValidationError):
        checkpoints.complete(settings, token, {"updates": []})
    monkeypatch.setattr(checkpoints, "write_text", original_write)
    original_index = checkpoints.update_paths
    monkeypatch.setattr(checkpoints, "update_paths", lambda *_: (_ for _ in ()).throw(OSError("Index unavailable")))
    with pytest.raises(OSError):
        checkpoints.complete(settings, token, payload)
    monkeypatch.setattr(checkpoints, "update_paths", original_index)
    assert checkpoints.complete(settings, token, payload)["complete"]
    assert (settings.vault / "concepts/decision.md").read_bytes() == first_bytes
    assert token not in read_json(checkpoints.cache_root(settings) / "pending.json")


@pytest.mark.parametrize("path", ["../outside.md", "_local/hidden.md", "AGENTS.md"])
def test_capture_paths_are_confined(settings, cheap_context, path):
    token = begin(settings)
    with pytest.raises((SafetyError, ValueError)):
        checkpoints.complete(settings, token, proposal(path))


def test_malformed_native_event_fails_open_without_echoing_input(settings, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO('{"prompt": "PRIVATE INPUT"}'))
    assert main(["--vault", str(settings.vault), "hook", "run", "--provider", "claude"]) == 0
    output = capsys.readouterr().out
    assert "PRIVATE INPUT" not in output and "systemMessage" in json.loads(output)


def test_manual_upsert_merges_sources_and_avoids_timestamp_churn(settings):
    values = dict(title="A result", description="Durable result", body="# A result\n\nAn observation.")
    upsert_page(settings, "concepts/result.md", source="urn:result:one", **values)
    upsert_page(settings, "concepts/result.md", source="urn:result:two", **values)
    before = read_page(settings, "concepts/result.md", track=False)
    assert len(before["metadata"]["sources"]) == 2
    assert not upsert_page(settings, "concepts/result.md", source="urn:result:two", **values)["changed"]
    assert read_page(settings, "concepts/result.md", track=False)["sha256"] == before["sha256"]


def test_conflict_can_be_revised_without_losing_previously_applied_index_rows(settings, cheap_context, monkeypatch):
    token = begin(settings)
    payload = proposal()
    payload["updates"].extend(proposal("concepts/second.md")["updates"])
    original_write = checkpoints.write_text
    def interruption(path, text):
        if path.name == "second.md":
            raise OSError("Interrupted")
        original_write(path, text)
    monkeypatch.setattr(checkpoints, "write_text", interruption)
    with pytest.raises(OSError):
        checkpoints.complete(settings, token, payload)
    monkeypatch.setattr(checkpoints, "write_text", original_write)
    snapshot = read_page(settings, "concepts/decision.md", track=False)
    payload["updates"][0]["expected_sha256"] = snapshot["sha256"]
    payload["updates"][0]["body"] = "# Decision\n\nA revised result."
    assert checkpoints.complete(settings, token, payload)["complete"]
    connection = index.connect(settings.vault)
    assert connection.execute("SELECT count(*) FROM pages").fetchone()[0] == 2
    connection.close()
