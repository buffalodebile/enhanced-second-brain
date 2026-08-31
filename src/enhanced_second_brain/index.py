from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import Settings
from .pages import iter_page_paths, parse_markdown
from .usage import record


@dataclass
class SearchResult:
    path: str
    title: str
    description: str
    score: float
    snippet: str


def database_path(vault: Path) -> Path:
    return vault / "_meta" / "cache" / "esb-fts.sqlite3"


def connect(vault: Path) -> sqlite3.Connection:
    path = database_path(vault)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA secure_delete=ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
          path TEXT PRIMARY KEY,
          content_hash TEXT NOT NULL,
          mtime_ns INTEGER NOT NULL,
          size INTEGER NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS pages USING fts5(
          path UNINDEXED,
          title,
          tags,
          description,
          headings,
          body,
          tokenize='unicode61 remove_diacritics 2'
        );
        """
    )
    return connection


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _page_row(path: Path, vault: Path) -> tuple[str, str, str, str, str, str]:
    page = parse_markdown(path, vault)
    tags = " ".join(str(tag) for tag in (page.metadata.get("tags") or []))
    headings = "\n".join(
        line.lstrip("# ") for line in page.body.splitlines() if line.startswith("#")
    )
    return (
        page.relative_path,
        str(page.metadata.get("title") or path.stem),
        tags,
        str(page.metadata.get("description") or page.metadata.get("summary") or ""),
        headings,
        page.body,
    )


def update(settings: Settings, *, verify_hashes: bool = False) -> dict[str, int]:
    vault = settings.vault
    current = {
        path.relative_to(vault).as_posix(): path for path in iter_page_paths(vault)
    }
    added = changed = removed = unchanged = 0
    connection = connect(vault)
    try:
        indexed = {
            row["path"]: row for row in connection.execute("SELECT * FROM documents")
        }
        for relative in sorted(indexed.keys() - current.keys()):
            connection.execute("DELETE FROM pages WHERE path = ?", (relative,))
            connection.execute("DELETE FROM documents WHERE path = ?", (relative,))
            removed += 1
        for relative, path in current.items():
            stat = path.stat()
            previous = indexed.get(relative)
            quick_same = (
                previous
                and previous["mtime_ns"] == stat.st_mtime_ns
                and previous["size"] == stat.st_size
            )
            digest = (
                previous["content_hash"]
                if quick_same and not verify_hashes
                else _hash(path)
            )
            if previous and quick_same and digest == previous["content_hash"]:
                unchanged += 1
                continue
            connection.execute("DELETE FROM pages WHERE path = ?", (relative,))
            connection.execute(
                "INSERT INTO pages(path,title,tags,description,headings,body) VALUES(?,?,?,?,?,?)",
                _page_row(path, vault),
            )
            connection.execute(
                "INSERT OR REPLACE INTO documents(path,content_hash,mtime_ns,size) VALUES(?,?,?,?)",
                (relative, digest, stat.st_mtime_ns, stat.st_size),
            )
            if previous:
                changed += 1
            else:
                added += 1
        connection.commit()
    finally:
        connection.close()
    return {
        "added": added,
        "changed": changed,
        "removed": removed,
        "unchanged": unchanged,
    }


def rebuild(settings: Settings) -> dict[str, int]:
    path = database_path(settings.vault)
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(path) + suffix)
        if candidate.exists():
            candidate.unlink()
    return update(settings, verify_hashes=True)


def _fts_query(query: str) -> str:
    tokens = re.findall(r"[^\W_]+", query, flags=re.UNICODE)
    return " OR ".join(f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens)


def query(
    settings: Settings, text: str, *, limit: int | None = None, track: bool = True
) -> list[SearchResult]:
    update(settings)
    expression = _fts_query(text)
    if not expression:
        return []
    requested = limit or settings.max_results
    sql = """
        SELECT path, title, description,
               -bm25(pages, 0.0, 8.0, 3.0, 5.0, 2.0, 1.0) AS score,
               snippet(pages, 5, '[', ']', ' … ', 20) AS snippet
        FROM pages WHERE pages MATCH ? ORDER BY bm25(pages, 0.0, 8.0, 3.0, 5.0, 2.0, 1.0)
        LIMIT ?
    """
    connection = connect(settings.vault)
    try:
        rows = connection.execute(sql, (expression, requested)).fetchall()
    finally:
        connection.close()
    results = [
        SearchResult(
            str(r["path"]),
            str(r["title"]),
            str(r["description"]),
            float(r["score"]),
            str(r["snippet"]),
        )
        for r in rows
    ]
    if track:
        for result in results:
            record(settings, "injected", result.path)
    return results


def status(settings: Settings) -> dict[str, Any]:
    path = database_path(settings.vault)
    if not path.exists():
        return {"exists": False, "path": str(path), "documents": 0, "bytes": 0}
    connection = connect(settings.vault)
    try:
        count = int(connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
    finally:
        connection.close()
    return {
        "exists": True,
        "path": str(path),
        "documents": count,
        "bytes": path.stat().st_size,
    }


def results_as_dict(results: list[SearchResult]) -> list[dict[str, Any]]:
    return [asdict(item) for item in results]
