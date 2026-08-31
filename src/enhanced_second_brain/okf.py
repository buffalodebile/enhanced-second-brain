from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .errors import ValidationError
from .pages import Page, dump_markdown, iter_page_paths, parse_markdown

OKF_FIELDS = ("type", "title", "description", "tags", "sources", "generated", "status")
EXTENSION_FIELDS = (
    "summary",
    "category",
    "relationships",
    "base_confidence",
    "lifecycle",
    "tier",
    "created",
    "updated",
)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _title_from(page: Page) -> str:
    heading = next(
        (line[2:].strip() for line in page.body.splitlines() if line.startswith("# ")),
        "",
    )
    return heading or page.path.stem.replace("-", " ").title()


def _type_from_category(value: Any) -> str:
    category = str(value or "note").strip().lower()
    singular = {
        "concepts": "concept",
        "projects": "project",
        "references": "reference",
        "skills": "skill",
        "entities": "entity",
        "analyses": "analysis",
    }.get(category, category)
    return singular.replace("-", " ").replace("_", " ").title()


def migrated_metadata(page: Page, *, now: str | None = None) -> dict[str, Any]:
    now = now or _now()
    old = dict(page.metadata)
    summary = str(old.get("summary") or old.get("description") or "").strip()
    if not summary:
        summary = next(
            (
                p.strip()
                for p in page.body.split("\n\n")
                if p.strip() and not p.startswith("#")
            ),
            "",
        )
        summary = " ".join(summary.split())[:500]
    title = str(old.get("title") or _title_from(page))
    result: dict[str, Any] = {
        "type": old.get("type") or _type_from_category(old.get("category")),
        "title": title,
        "description": summary,
        "tags": old.get("tags") if isinstance(old.get("tags"), list) else [],
        "sources": _normalize_sources(old.get("sources")),
        "generated": _normalize_generated(old.get("generated"), now),
        "status": old.get("status") or old.get("lifecycle") or "draft",
    }
    for key, value in old.items():
        if key not in result:
            result[key] = value
    result["summary"] = summary
    result.setdefault("category", "concepts")
    result.setdefault("relationships", [])
    result.setdefault("base_confidence", 0.5)
    result.setdefault("lifecycle", str(result["status"]))
    result.setdefault("tier", "supporting")
    result.setdefault("created", now)
    result.setdefault("updated", now)
    return result


def _normalize_sources(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict) and item.get("resource"):
            normalized.append({"resource": str(item["resource"])})
        elif isinstance(item, str):
            normalized.append({"resource": item})
    return normalized


def _normalize_generated(value: Any, now: str) -> dict[str, str]:
    if isinstance(value, dict):
        return {
            "by": str(value.get("by") or "process:enhanced-second-brain"),
            "at": str(value.get("at") or now),
        }
    return {"by": "process:enhanced-second-brain", "at": now}


def audit_page(page: Page, *, strict: bool = True) -> list[str]:
    errors: list[str] = []
    data = page.metadata
    for key in OKF_FIELDS:
        if key not in data:
            errors.append(f"missing field: {key}")
    if "tags" in data and not isinstance(data["tags"], list):
        errors.append("tags must be a list")
    if "sources" in data and (
        not isinstance(data["sources"], list)
        or any(
            not isinstance(item, dict) or not item.get("resource")
            for item in data["sources"]
        )
    ):
        errors.append("sources must be a list of objects with resource")
    generated = data.get("generated")
    if generated is not None and (
        not isinstance(generated, dict)
        or not generated.get("by")
        or not generated.get("at")
    ):
        errors.append("generated must contain by and at")
    if strict:
        for key in EXTENSION_FIELDS:
            if key not in data:
                errors.append(f"missing Enhanced OKF extension: {key}")
        if data.get("description") != data.get("summary"):
            errors.append("description and summary must match")
    return errors


def audit_vault(vault: Path, *, strict: bool = True) -> dict[str, Any]:
    pages: dict[str, list[str]] = {}
    for path in iter_page_paths(vault):
        try:
            page = parse_markdown(path, vault)
            errors = audit_page(page, strict=strict)
        except (OSError, UnicodeError, yaml.YAMLError, ValidationError) as exc:
            errors = [str(exc)]
        if errors:
            pages[path.relative_to(vault).as_posix()] = errors
    return {
        "valid": not pages,
        "checked": sum(1 for _ in iter_page_paths(vault)),
        "errors": pages,
    }


def migrate_vault(vault: Path, *, write: bool = False) -> dict[str, Any]:
    changed: list[str] = []
    now = _now()
    for path in iter_page_paths(vault):
        page = parse_markdown(path, vault)
        metadata = migrated_metadata(page, now=now)
        desired = dump_markdown(metadata, page.body)
        current = path.read_text(encoding="utf-8-sig")
        if desired != current:
            changed.append(page.relative_path)
            if write:
                path.write_text(desired, encoding="utf-8", newline="\n")
    return {"changed": changed, "count": len(changed), "written": write}
