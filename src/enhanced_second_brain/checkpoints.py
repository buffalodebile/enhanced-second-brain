"""Validated, resumable batches. Semantic selection belongs to the current agent."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from filelock import FileLock

from .atomic import read_json, write_json, write_text
from .config import Settings
from .errors import SafetyError, ValidationError
from .index import update_paths
from .okf import audit_page, migrated_metadata
from .pages import Page, dump_markdown, is_knowledge_path, parse_markdown, safe_relative


def digest(value: str | bytes) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def cache_root(settings: Settings) -> Path:
    root = settings.vault / "_meta" / "cache" / "hooks"
    root.mkdir(parents=True, exist_ok=True)
    return root


def turn_path(settings: Settings, turn_id: str) -> Path:
    return cache_root(settings) / "turns" / (digest(turn_id) + ".json")


def load_turn(settings: Settings, turn_id: str) -> dict[str, Any]:
    result = read_json(turn_path(settings, turn_id))
    if not isinstance(result, dict) or result.get("turn_id") != turn_id:
        raise ValidationError("Unknown capture turn; use the turn id injected by the hook")
    return result


def pending(settings: Settings, turn_id: str, reason: str | None) -> None:
    path = cache_root(settings) / "pending.json"
    with FileLock(str(path) + ".lock", timeout=1):
        entries = read_json(path, {})
        if reason is None:
            entries.pop(turn_id, None)
        else:
            entries[turn_id] = reason
        write_json(path, entries)


def _render(settings: Settings, item: dict[str, Any], now: str) -> dict[str, Any]:
    raw_path = item.get("path")
    if not isinstance(raw_path, str):
        raise ValidationError("Each update requires a relative path")
    path, relative = safe_relative(settings.vault, raw_path)
    if Path(raw_path).is_absolute() or not is_knowledge_path(settings.vault, path):
        raise SafetyError("Updates require relative knowledge Markdown paths")
    if "expected_sha256" not in item:
        raise ValidationError("Each update requires expected_sha256 (null for a new page)")
    snapshot = path.read_bytes() if path.exists() else None
    actual = digest(snapshot) if snapshot is not None else None
    if item["expected_sha256"] != actual:
        raise SafetyError(f"Concurrent modification: {relative}; read and merge the page again")
    old = parse_markdown(path, settings.vault, text=snapshot.decode("utf-8-sig")) if snapshot is not None else None
    proposed = item.get("metadata")
    body = item.get("body")
    if not isinstance(proposed, dict) or not isinstance(body, str):
        raise ValidationError("Each update requires metadata and a complete Markdown body")
    for field in ("title", "description"):
        if not isinstance(proposed.get(field), str) or not proposed[field].strip():
            raise ValidationError(f"Update metadata requires a nonempty {field}")
    seed = old or Page(path, relative, {}, body)
    metadata = migrated_metadata(seed, now=now)
    # Preserve extensions by default, while allowing the agent to update typed relations.
    metadata.update(proposed)
    metadata["summary"] = metadata["description"]
    sources = list(old.metadata.get("sources", [])) if old else []
    supplied = proposed.get("sources", [])
    if not isinstance(supplied, list) or any(
        not isinstance(source, dict) or not source.get("resource") for source in supplied
    ):
        raise ValidationError("sources must be a list of objects with resource")
    for source in supplied:
        if source not in sources:
            sources.append(source)
    metadata["sources"] = sources
    if old:
        metadata["created"] = old.metadata.get("created", metadata["created"])
    # Ignore generated timestamps in the proposal when deciding whether anything changed.
    comparable = dict(metadata)
    for field in ("updated", "generated"):
        comparable.pop(field, None)
    previous = dict(old.metadata) if old else None
    if previous is not None:
        for field in ("updated", "generated"):
            previous.pop(field, None)
    unchanged = old is not None and previous == comparable and old.body.rstrip() == body.rstrip()
    if unchanged:
        content = snapshot.decode("utf-8")
    else:
        metadata["updated"] = now
        metadata["generated"] = {"by": "process:enhanced-second-brain", "at": now}
        content = dump_markdown(metadata, body)
    errors = audit_page(Page(path, relative, metadata, body), strict=True)
    if errors:
        raise ValidationError(f"{relative}: {'; '.join(errors)}")
    return {"path": relative, "before": actual, "after": digest(content), "content": content,
            "changed": not unchanged}


def complete(settings: Settings, turn_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get("updates"), list):
        raise ValidationError('Checkpoint must be an object with an "updates" list')
    updates = payload["updates"]
    if any(not isinstance(item, dict) for item in updates):
        raise ValidationError("Updates must be objects")
    fingerprint = digest(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    state_path = turn_path(settings, turn_id)
    with FileLock(str(state_path) + ".lock", timeout=1):
        state = load_turn(settings, turn_id)
        if state.get("status") == "complete":
            if state.get("checkpoint_hash") != fingerprint:
                raise ValidationError("This turn already has a different completed checkpoint")
            pending(settings, turn_id, None)
            return {"complete": True, "duplicate": True, "changed": state.get("changed", [])}
        # Empty receipts don't open SQLite or acquire the knowledge writer lock.
        if not updates:
            if state.get("journal"):
                raise ValidationError("An applying checkpoint must be recovered before an empty receipt")
            state.update(status="complete", checkpoint_hash=fingerprint, changed=[])
            write_json(state_path, state)
            pending(settings, turn_id, None)
            return {"complete": True, "changed": []}
        try:
            with FileLock(str(cache_root(settings) / "writer.lock"), timeout=5):
                journal = state.get("journal")
                if journal and state.get("checkpoint_hash") != fingerprint:
                    # A revised merge may replace a failed proposal after rereading all pages.
                    prior_paths = {item["path"] for item in journal}
                    if not prior_paths.issubset({item.get("path") for item in updates}):
                        raise ValidationError("A revised applying checkpoint must include every prior page")
                    state["repair_paths"] = sorted(prior_paths)
                    journal = None
                if journal is None:
                    now = datetime.now(UTC).isoformat(timespec="seconds")
                    journal = [_render(settings, item, now) for item in updates]
                    paths = [item["path"].casefold() for item in journal]
                    if len(paths) != len(set(paths)):
                        raise ValidationError("Duplicate page paths in checkpoint")
                    state.update(journal=journal, checkpoint_hash=fingerprint, status="applying")
                    write_json(state_path, state)
                # Preflight every page before making any writes. Already-applied pages are safe.
                for item in journal:
                    path, _ = safe_relative(settings.vault, item["path"])
                    actual = digest(path.read_bytes()) if path.exists() else None
                    if actual not in (item["before"], item["after"]):
                        raise SafetyError(f"Concurrent modification: {item['path']}; read and merge again")
                changed = sorted(set(state.get("repair_paths", [])) | {item["path"] for item in journal if item["changed"]})
                for item in journal:
                    path, _ = safe_relative(settings.vault, item["path"])
                    if item["changed"] and (not path.exists() or digest(path.read_bytes()) != item["after"]):
                        write_text(path, item["content"])
                if changed:
                    update_paths(settings, changed)
                state.update(status="complete", changed=changed)
                state.pop("journal", None)
                state.pop("repair_paths", None)
                write_json(state_path, state)
                pending(settings, turn_id, None)
                return {"complete": True, "changed": changed}
        except Exception:
            pending(settings, turn_id, "Checkpoint failed; reread affected pages and retry")
            raise
