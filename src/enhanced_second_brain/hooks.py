"""Provider adapters around one end-of-turn capture state machine."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from filelock import FileLock

from .atomic import read_json, write_json
from .checkpoints import cache_root, digest, load_turn, pending, turn_path
from .config import Settings
from .context import prepare
from .errors import ValidationError

EVENTS = {"UserPromptSubmit": "begin", "Stop": "end", "SessionEnd": "session_end"}


def _session_path(settings: Settings, provider: str, session_id: str) -> Path:
    return cache_root(settings) / "sessions" / (digest(provider + ":" + session_id) + ".json")


def _instructions(settings: Settings, turn_id: str, outstanding: dict) -> str:
    from .automation import _executable
    from .installer import _agent_command

    command = _agent_command(settings.vault, _executable())
    return (
        f"Enhanced Second Brain capture turn: {turn_id}. Context lookup already ran; do not repeat it.\n"
        "Before your final answer, decide whether this work produced durable knowledge: a decision, "
        "resolved incident, verified result, lasting preference or reusable lesson. Ignore trivial "
        "exchanges and facts immediately reconstructible from code. Search/read relevant existing "
        "pages and merge into them before creating a new page. Preserve sources and OKF extensions; "
        "never invent verification. Use relative .md body links.\n"
        f"Write a temporary JSON file outside the vault root and run {command} checkpoint complete "
        f"--turn-id {turn_id} --input <file>. Format: {{\"updates\": [{{\"path\": "
        "\"concepts/example.md\", \"expected_sha256\": null, \"metadata\": {\"title\": "
        "\"...\", \"description\": \"...\", \"sources\": [{\"resource\": \"...\"}]}, "
        "\"body\": \"# ...\"}]}. For existing pages use the sha256 returned by page read. "
        "For no durable novelty, use {\"updates\": []}. Delete the temporary input after success. "
        "Do not run full reconcile after a checkpoint; touched pages are validated and indexed. "
        "Do not store credentials or raw transcripts.\n"
        + ("Unfinished captures (not successful): " + json.dumps(outstanding) + ". "
           "Read their local state with checkpoint status --turn-id ID, repair any applying journal "
           "before revising its proposal, and recover what evidence is still available. Report "
           "unrecoverable context honestly; never invent knowledge.\n" if outstanding else "")
    )


def _native(provider: str, event: str, result: dict[str, Any]) -> dict[str, Any]:
    if provider == "generic":
        return result
    output: dict[str, Any] = {}
    if result.get("warning"):
        output["systemMessage"] = result["warning"]
    if event == "begin":
        output["hookSpecificOutput"] = {
            "hookEventName": "UserPromptSubmit", "additionalContext": result["context"]
        }
    if result.get("action") == "continue":
        output.update(decision="block", reason=result["reason"])
    return output


def run(settings: Settings, provider: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Never decide semantics, read transcripts, or launch a model at Stop."""
    if not isinstance(payload, dict) or not isinstance(payload.get("session_id"), str) or not payload["session_id"]:
        raise ValidationError("Hook event requires a nonempty session_id")
    event = payload.get("event") if provider == "generic" else EVENTS.get(payload.get("hook_event_name"))
    if event not in ("begin", "end", "session_end"):
        raise ValidationError("Unsupported hook event")
    session_path = _session_path(settings, provider, payload["session_id"])
    session_path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(session_path) + ".lock", timeout=1):
        session = read_json(session_path, {})
        current = session.get("current")
        session_key = digest(provider + ":" + payload["session_id"])
        if event == "begin":
            prompt = payload.get("prompt", "")
            if not isinstance(prompt, str):
                raise ValidationError("prompt must be text")
            # Codex creates a synthetic user prompt for a Stop continuation. Reuse its
            # original capture token and never advance the maintenance counter twice.
            technical = current and prompt.startswith(f"ESB capture continuation {current}:")
            event_id = payload.get("event_id") or payload.get("turn_id")
            if provider == "generic" and not event_id:
                raise ValidationError("Generic begin requires event_id or turn_id")
            if not event_id:
                # Claude has no turn id. Its transcript position disambiguates repeated
                # identical human prompts without reading or retaining their text.
                transcript = payload.get("transcript_path")
                position = ""
                if isinstance(transcript, str):
                    try:
                        stat = Path(transcript).expanduser().stat()
                        position = f"{stat.st_size}:{stat.st_mtime_ns}"
                    except OSError:
                        pass
                event_id = digest(prompt + ":" + position) if position else uuid.uuid4().hex
            event_key = digest(str(event_id))
            event_path = cache_root(settings) / "events" / (digest(session_key + event_key) + ".json")
            seen = read_json(event_path)
            if technical or seen:
                prepared = None
                token = current if technical else seen["turn_id"]
            else:
                if current and load_turn(settings, current).get("status") != "complete":
                    pending(settings, current, "Interrupted or unfinished capture")
                token = uuid.uuid4().hex
                write_json(turn_path(settings, token), {
                    "turn_id": token, "status": "open", "reminded": False,
                    "session_key": session_key,
                })
                # Store the id before running context, so failed lookups are not
                # mistaken for successful capture and can be reported on the next turn.
                session.update(current=token, event_key=event_key)
                write_json(session_path, session)
                write_json(event_path, {"turn_id": token})
                try:
                    prepared = prepare(settings, prompt)
                except Exception:
                    pending(settings, token, "Context lookup failed; use explicit context lookup")
                    raise
            outstanding = read_json(cache_root(settings) / "pending.json", {})
            text = _instructions(settings, token, outstanding)
            if prepared is not None:
                text += "\n" + json.dumps({"context": prepared["context"], "maintenance": prepared["maintenance"]}, ensure_ascii=False)
            return _native(provider, event, {"action": "allow", "turn_id": token, "context": text})
        if provider == "generic" and payload.get("turn_id"):
            current = payload["turn_id"]
        elif provider == "codex" and payload.get("turn_id"):
            event_path = cache_root(settings) / "events" / (digest(session_key + digest(str(payload["turn_id"]))) + ".json")
            seen = read_json(event_path)
            if seen:
                current = seen["turn_id"]
        if not current:
            return _native(provider, event, {"action": "allow"})
        path = turn_path(settings, current)
        with FileLock(str(path) + ".lock", timeout=1):
            state = load_turn(settings, current)
            if state.get("session_key") != session_key:
                raise ValidationError("Capture turn does not belong to this session")
            if state.get("status") == "complete":
                return _native(provider, event, {"action": "allow", "turn_id": current})
            if event == "end" and not state.get("reminded") and not payload.get("stop_hook_active", False):
                state["reminded"] = True
                write_json(path, state)
                reason = f"ESB capture continuation {current}: complete the durable-knowledge checkpoint "
                reason += "described in your injected instructions (an empty updates list is valid). "
                reason += "This is the only reminder; avoid redoing the user task."
                return _native(provider, event, {"action": "continue", "turn_id": current, "reason": reason})
            pending(settings, current, "Capture incomplete after reminder or session closure")
            return _native(provider, event, {
                "action": "allow", "turn_id": current,
                "warning": "Enhanced Second Brain: capture remains unfinished; it will be reported at the next prompt.",
            })
