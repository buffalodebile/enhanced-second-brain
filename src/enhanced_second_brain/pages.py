from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from .errors import SafetyError, ValidationError

EXCLUDED_PARTS = {
    "_raw",
    "_archives",
    "_meta",
    ".git",
    ".obsidian",
    "exports",
    "wiki-export",
    "journal",
}
EXCLUDED_FILES = {
    "index.md",
    "hot.md",
    "log.md",
    "agents.md",
    "claude.md",
    "copilot-instructions.md",
}
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)#]+\.md)(?:#[^)]+)?\)")


@dataclass
class Page:
    path: Path
    relative_path: str
    metadata: dict[str, Any]
    body: str


def safe_relative(
    vault: Path, raw: str | Path, *, must_exist: bool = False
) -> tuple[Path, str]:
    root = vault.resolve()
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=must_exist)
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise SafetyError(f"Path escapes the vault: {raw}") from exc
    return resolved, PurePosixPath(relative).as_posix()


def is_knowledge_path(vault: Path, path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(vault.resolve())
    except ValueError:
        return False
    if (
        path.suffix.lower() != ".md"
        or path.name.lower() in EXCLUDED_FILES
        or path.name.startswith(".")
    ):
        return False
    return not any(
        part in EXCLUDED_PARTS or part.startswith(".") for part in rel.parts[:-1]
    )


def iter_page_paths(vault: Path) -> Iterable[Path]:
    for path in sorted(vault.rglob("*.md")):
        if is_knowledge_path(vault, path):
            yield path


def parse_markdown(path: Path, vault: Path | None = None) -> Page:
    # Accept ordinary UTF-8 and strip the BOM commonly emitted by Windows
    # editors so a valid frontmatter fence is never mistaken for body text.
    text = path.read_text(encoding="utf-8-sig")
    metadata: dict[str, Any] = {}
    body = text
    if text.startswith(("---\n", "---\r\n")):
        lines = text.splitlines(keepends=True)
        closing = next(
            (i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), None
        )
        if closing is None:
            raise ValidationError(f"Unclosed YAML frontmatter: {path}")
        raw = "".join(lines[1:closing])
        parsed = yaml.safe_load(raw) or {}
        if not isinstance(parsed, dict):
            raise ValidationError(f"Frontmatter must be a mapping: {path}")
        metadata = parsed
        body = "".join(lines[closing + 1 :]).lstrip("\r\n")
    root = vault or path.parent
    _, relative = safe_relative(root, path, must_exist=True)
    return Page(path, relative, metadata, body)


def dump_markdown(metadata: dict[str, Any], body: str) -> str:
    yaml_text = yaml.safe_dump(
        metadata, allow_unicode=True, sort_keys=False, width=1000
    ).strip()
    return f"---\n{yaml_text}\n---\n\n{body.rstrip()}\n"


def page_links(page: Page) -> list[str]:
    links = WIKILINK_RE.findall(page.body)
    links.extend(MARKDOWN_LINK_RE.findall(page.body))
    relationships = page.metadata.get("relationships") or []
    if isinstance(relationships, list):
        for item in relationships:
            if isinstance(item, dict) and item.get("target"):
                target = str(item["target"])
                match = WIKILINK_RE.search(target)
                links.append(match.group(1) if match else target)
    return links


def resolve_link(source: Page, link: str, known: dict[str, str]) -> str | None:
    normalized = link.replace("\\", "/").strip()
    if normalized.endswith(".md"):
        direct = PurePosixPath(source.relative_path).parent.joinpath(normalized)
        collapsed = str(PurePosixPath(direct)).replace("/./", "/")
        # Resolve '..' without touching the filesystem.
        parts: list[str] = []
        for part in PurePosixPath(collapsed).parts:
            if part == "..":
                if parts:
                    parts.pop()
            elif part != ".":
                parts.append(part)
        candidate = "/".join(parts)
        return (
            candidate
            if candidate in known.values()
            else known.get(normalized.removesuffix(".md").lower())
        )
    key = normalized.removesuffix(".md").lower()
    return known.get(key) or known.get(PurePosixPath(key).name)
