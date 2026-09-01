from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .config import Settings
from .context import prepare as prepare_context
from .index import query, results_as_dict, status, update
from .okf import audit_page, migrated_metadata
from .pages import dump_markdown, is_knowledge_path, parse_markdown, safe_relative
from .usage import record


def read_page(
    settings: Settings, raw_path: str, *, track: bool = True
) -> dict[str, Any]:
    path, relative = safe_relative(settings.vault, raw_path, must_exist=True)
    if not is_knowledge_path(settings.vault, path):
        raise ValueError("Page must be a knowledge Markdown file")
    page = parse_markdown(path, settings.vault)
    if track:
        record(settings, "opened", relative)
    return {"path": relative, "metadata": page.metadata, "body": page.body}


def upsert_page(
    settings: Settings,
    raw_path: str,
    *,
    title: str,
    description: str,
    body: str,
    tags: list[str] | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    path, relative = safe_relative(settings.vault, raw_path)
    if not is_knowledge_path(settings.vault, path):
        raise ValueError("Page must be a knowledge Markdown file")
    old = parse_markdown(path, settings.vault) if path.exists() else None
    now = datetime.now(UTC).isoformat(timespec="seconds")
    seed = old or type("Seed", (), {"metadata": {}, "body": body, "path": path})()
    metadata = migrated_metadata(seed, now=now)
    metadata.update(
        {
            "title": title,
            "description": description,
            "summary": description,
            "tags": tags if tags is not None else list(metadata.get("tags") or []),
            "updated": now,
            "generated": {"by": "process:enhanced-second-brain", "at": now},
        }
    )
    if source:
        metadata["sources"] = [{"resource": source}]
    page_like = type("PageLike", (), {"metadata": metadata, "body": body})()
    errors = audit_page(page_like, strict=True)
    if errors:
        raise ValueError("; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_markdown(metadata, body), encoding="utf-8", newline="\n")
    update(settings)
    return {"path": relative, "created": old is None}


def search(
    settings: Settings, text: str, *, limit: int | None = None
) -> list[dict[str, Any]]:
    return results_as_dict(query(settings, text, limit=limit, track=True))


def cite(settings: Settings, path: str) -> dict[str, Any]:
    return record(settings, "cited", path)


def system_status(settings: Settings) -> dict[str, Any]:
    return {"vault": str(settings.vault), "index": status(settings)}


def agent_context(
    settings: Settings, text: str, *, limit: int | None = None
) -> dict[str, Any]:
    return prepare_context(settings, text, limit=limit)
