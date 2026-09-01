from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from .config import Settings
from .errors import SafetyError
from .okf import audit_vault
from .pages import dump_markdown, parse_markdown, safe_relative
from .utility import scores


def _date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def candidates(
    settings: Settings, *, now: datetime | None = None
) -> list[dict[str, Any]]:
    now = now or datetime.now(UTC)
    selected = []
    for row in scores(settings, now=now):
        page = parse_markdown(settings.vault / row["path"], settings.vault)
        meta = page.metadata
        tags = {str(tag).lower().lstrip("#") for tag in (meta.get("tags") or [])}
        states = {
            str(meta.get("status", "")).lower(),
            str(meta.get("lifecycle", "")).lower(),
        }
        protections = []
        if str(meta.get("tier", "")).lower() == "core":
            protections.append("core")
        if "verified" in states:
            protections.append("verified")
        if (
            bool(meta.get("confidential"))
            or "confidential" in tags
            or "confidentiel" in tags
        ):
            protections.append("confidential")
        if (
            "rejected" in states
            or "rejected" in tags
            or "rejete" in tags
            or "rejected" in page.path.stem.lower()
        ):
            protections.append("rejected")
        if row["backlinks"] >= settings.archive.minimum_backlinks:
            protections.append("linked")
        if page.path.parent.name == "projects" or (
            "projects" in page.path.parts and page.path.stem == page.path.parent.name
        ):
            protections.append("project-hub")
        last_used = _date(row["last_used"])
        inactive_days = (
            float("inf")
            if last_used is None
            else (now - last_used).total_seconds() / 86400
        )
        qualifies = (
            not protections
            and row["age_days"] >= settings.archive.minimum_age_days
            and inactive_days >= settings.archive.inactive_days
            and row["decayed_effective_usage"]
            <= settings.archive.max_effective_usage
            and row["strength"] <= settings.archive.cold_threshold
        )
        if qualifies:
            selected.append(
                {
                    **row,
                    "inactive_days": None
                    if inactive_days == float("inf")
                    else round(inactive_days, 1),
                    "protections": protections,
                }
            )
    return selected


def apply(
    settings: Settings, paths: list[str], *, archive_date: date | None = None
) -> dict[str, Any]:
    audit = audit_vault(settings.vault, strict=True)
    if not audit["valid"]:
        raise SafetyError("Strict OKF audit failed; refusing to archive")
    allowed = {row["path"] for row in candidates(settings)}
    requested = set(paths)
    rejected = sorted(requested - allowed)
    if rejected:
        raise SafetyError(f"Not eligible for archival: {', '.join(rejected)}")
    stamp = (archive_date or datetime.now(UTC).date()).isoformat()
    root = settings.vault / "_archives" / "pruned" / stamp
    moved = []
    destinations = []
    for raw in sorted(requested):
        _, relative = safe_relative(settings.vault, raw, must_exist=True)
        destination = root / Path(relative)
        if destination.exists():
            raise SafetyError(f"Archive destination already exists: {destination}")
        destinations.append((raw, relative, destination))
    for raw, relative, destination in destinations:
        source, _ = safe_relative(settings.vault, raw, must_exist=True)
        destination.parent.mkdir(parents=True, exist_ok=True)
        page = parse_markdown(source, settings.vault)
        metadata = dict(page.metadata)
        metadata["archive_previous"] = {
            key: metadata[key]
            for key in ("status", "lifecycle", "lifecycle_changed", "archive_reason")
            if key in metadata
        }
        metadata["lifecycle"] = "archived"
        metadata["status"] = "archived"
        metadata["lifecycle_changed"] = stamp
        metadata["archive_reason"] = (
            "Automatically selected by the configured cold-utility policy."
        )
        destination.write_text(
            dump_markdown(metadata, page.body), encoding="utf-8", newline="\n"
        )
        source.unlink()
        moved.append(
            {"from": relative, "to": destination.relative_to(settings.vault).as_posix()}
        )
    if moved:
        root.mkdir(parents=True, exist_ok=True)
        (root / "prune-meta.json").write_text(
            json.dumps({"date": stamp, "moved": moved}, indent=2) + "\n",
            encoding="utf-8",
        )
    return {"moved": moved, "count": len(moved)}


def restore(settings: Settings, archive_path: str) -> dict[str, str]:
    source, relative = safe_relative(settings.vault, archive_path, must_exist=True)
    marker = "_archives/pruned/"
    if marker not in relative:
        raise SafetyError("Restore source is not a pruned archive")
    remainder = relative.split("/", 3)[3]
    destination, destination_relative = safe_relative(settings.vault, remainder)
    if destination.exists():
        raise SafetyError(f"Restore destination already exists: {destination_relative}")
    page = parse_markdown(source, settings.vault)
    metadata = dict(page.metadata)
    previous = metadata.pop("archive_previous", None)
    for key in ("status", "lifecycle", "lifecycle_changed", "archive_reason"):
        metadata.pop(key, None)
    if isinstance(previous, dict):
        metadata.update(previous)
    else:
        metadata.update({"status": "draft", "lifecycle": "draft"})
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        dump_markdown(metadata, page.body), encoding="utf-8", newline="\n"
    )
    source.unlink()
    return {"from": relative, "to": destination_relative}
