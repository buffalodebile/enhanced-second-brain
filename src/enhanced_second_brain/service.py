from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .config import Settings
from .context import prepare as prepare_context
from .index import query, results_as_dict, status, update_paths
from .pages import is_knowledge_path, parse_markdown, safe_relative
from .usage import record


def read_page(
    settings: Settings, raw_path: str, *, track: bool = True
) -> dict[str, Any]:
    path, relative = safe_relative(settings.vault, raw_path, must_exist=True)
    if not is_knowledge_path(settings.vault, path):
        raise ValueError("Page must be a knowledge Markdown file")
    snapshot = path.read_bytes()
    page = parse_markdown(path, settings.vault, text=snapshot.decode("utf-8-sig"))
    if track:
        record(settings, "opened", relative)
    from .checkpoints import digest

    return {"path": relative, "metadata": page.metadata, "body": page.body,
            "sha256": digest(snapshot)}


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
    from filelock import FileLock
    from .atomic import write_text
    from .checkpoints import _render, cache_root, digest

    path, relative = safe_relative(settings.vault, raw_path)
    if not is_knowledge_path(settings.vault, path):
        raise ValueError("Page must be a knowledge Markdown file")
    with FileLock(str(cache_root(settings) / "writer.lock"), timeout=5):
        exists = path.exists()
        metadata = {"title": title, "description": description}
        if tags is not None:
            metadata["tags"] = tags
        if source:
            metadata["sources"] = [{"resource": source}]
        item = _render(settings, {
            "path": relative, "expected_sha256": digest(path.read_bytes()) if exists else None,
            "metadata": metadata, "body": body,
        }, datetime.now(UTC).isoformat(timespec="seconds"))
        if item["changed"]:
            write_text(path, item["content"])
            update_paths(settings, [relative])
        return {"path": relative, "created": not exists, "changed": item["changed"]}


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
