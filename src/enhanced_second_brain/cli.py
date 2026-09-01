from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .backup import backup
from .benchmark import run as run_benchmark
from .config import DEFAULT_TOML, Settings, ensure_vault, resolve_settings
from .errors import ESBError
from .index import query, rebuild, results_as_dict, status, update
from .installer import install as install_toolkit
from .okf import audit_vault, migrate_vault
from .prune import apply as apply_prune
from .prune import candidates, restore
from .service import read_page, upsert_page
from .usage import record
from .utility import persist_scores, scores


def _json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def _settings(args: argparse.Namespace, *, require: bool = True) -> Settings:
    settings = resolve_settings(args.vault)
    if require:
        ensure_vault(settings)
    return settings


def _init(args: argparse.Namespace) -> dict[str, Any]:
    if not args.vault:
        raise ESBError("init requires --vault PATH")
    vault = Path(args.vault).expanduser().resolve()
    vault.mkdir(parents=True, exist_ok=True)
    for directory in (
        "concepts",
        "projects",
        "references",
        "_meta/cache",
        "_archives/pruned",
    ):
        (vault / directory).mkdir(parents=True, exist_ok=True)
    config = vault / "second-brain.toml"
    if not config.exists():
        config.write_text(DEFAULT_TOML, encoding="utf-8", newline="\n")
    ignore = vault / ".gitignore"
    additions = [
        "_meta/cache/",
        "_meta/usage.jsonl",
        "_meta/usage.jsonl.lock",
        "_meta/utility.json",
    ]
    existing = (
        ignore.read_text(encoding="utf-8").splitlines() if ignore.exists() else []
    )
    merged = existing + [line for line in additions if line not in existing]
    ignore.write_text("\n".join(merged) + "\n", encoding="utf-8", newline="\n")
    return {"vault": str(vault), "config": str(config), "created": True}


def _doctor(settings: Settings) -> dict[str, Any]:
    memory = sqlite3.connect(":memory:")
    try:
        memory.execute("CREATE VIRTUAL TABLE fts_probe USING fts5(content)")
        has_fts5 = True
    except sqlite3.OperationalError:
        has_fts5 = False
    finally:
        memory.close()
    return {
        "version": __version__,
        "vault": str(settings.vault),
        "config": str(settings.config_file) if settings.config_file else None,
        "fts5": has_fts5,
        "okf": audit_vault(settings.vault, strict=True),
        "index": status(settings),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="esb", description="Enhanced Second Brain toolkit"
    )
    parser.add_argument(
        "--vault", help="Vault path (overrides ESB_VAULT_PATH and second-brain.toml)"
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    install = commands.add_parser("install")
    install.add_argument("--no-automation", action="store_true")
    install.add_argument(
        "--dry-run-automation", action="store_true", help=argparse.SUPPRESS
    )
    commands.add_parser("doctor")

    okf = commands.add_parser("okf").add_subparsers(dest="okf_command", required=True)
    migrate = okf.add_parser("migrate")
    migrate.add_argument("--write", action="store_true")
    audit = okf.add_parser("audit")
    audit.add_argument("--no-strict", action="store_true")

    index = commands.add_parser("index").add_subparsers(
        dest="index_command", required=True
    )
    update_parser = index.add_parser("update")
    update_parser.add_argument("--verify-hashes", action="store_true")
    search = index.add_parser("query")
    search.add_argument("query")
    search.add_argument("--limit", type=int)
    index.add_parser("status")
    index.add_parser("rebuild")

    page = commands.add_parser("page").add_subparsers(
        dest="page_command", required=True
    )
    read = page.add_parser("read")
    read.add_argument("path")
    upsert = page.add_parser("upsert")
    upsert.add_argument("path")
    upsert.add_argument("--title", required=True)
    upsert.add_argument("--description", required=True)
    upsert.add_argument("--body", required=True)
    upsert.add_argument("--tag", action="append")
    upsert.add_argument("--source")

    usage = commands.add_parser("usage").add_subparsers(
        dest="usage_command", required=True
    )
    usage_record = usage.add_parser("record")
    usage_record.add_argument("event", choices=("injected", "opened", "cited"))
    usage_record.add_argument("path")
    commands.add_parser("score")

    prune = commands.add_parser("prune").add_subparsers(
        dest="prune_command", required=True
    )
    prune.add_parser("candidates")
    prune_apply = prune.add_parser("apply")
    prune_apply.add_argument("paths", nargs="*")
    prune_apply.add_argument("--all-candidates", action="store_true")
    prune_restore = prune.add_parser("restore")
    prune_restore.add_argument("path")

    commands.add_parser("reconcile")
    benchmark = commands.add_parser("benchmark")
    benchmark.add_argument("dataset", type=Path)
    benchmark.add_argument("--top-k", type=int, default=5)
    benchmark.add_argument("--max-p95-ms", type=float)
    commands.add_parser("backup")
    return parser


def dispatch(args: argparse.Namespace) -> Any:
    if args.command == "init":
        return _init(args)
    if args.command == "install":
        if not args.vault:
            raise ESBError("install requires --vault PATH")
        return install_toolkit(
            Path(args.vault),
            automation=not args.no_automation,
            dry_run_automation=args.dry_run_automation,
        )
    settings = _settings(args)
    if args.command == "doctor":
        return _doctor(settings)
    if args.command == "okf":
        if args.okf_command == "migrate":
            return migrate_vault(settings.vault, write=args.write)
        return audit_vault(settings.vault, strict=not args.no_strict)
    if args.command == "index":
        if args.index_command == "update":
            return update(settings, verify_hashes=args.verify_hashes)
        if args.index_command == "query":
            return results_as_dict(query(settings, args.query, limit=args.limit))
        if args.index_command == "rebuild":
            return rebuild(settings)
        return status(settings)
    if args.command == "page":
        if args.page_command == "read":
            return read_page(settings, args.path)
        return upsert_page(
            settings,
            args.path,
            title=args.title,
            description=args.description,
            body=args.body,
            tags=args.tag,
            source=args.source,
        )
    if args.command == "usage":
        return record(settings, args.event, args.path)
    if args.command == "score":
        return scores(settings)
    if args.command == "prune":
        if args.prune_command == "candidates":
            return candidates(settings)
        if args.prune_command == "restore":
            return restore(settings, args.path)
        if args.all_candidates and args.paths:
            raise ESBError("Choose explicit paths or --all-candidates, not both")
        selected = (
            [row["path"] for row in candidates(settings)]
            if args.all_candidates
            else args.paths
        )
        if args.all_candidates and not selected:
            return {"moved": [], "count": 0}
        if not selected:
            raise ESBError("Provide page paths or --all-candidates")
        return apply_prune(settings, selected)
    if args.command == "reconcile":
        migration = migrate_vault(settings.vault, write=True)
        audit = audit_vault(settings.vault, strict=True)
        if not audit["valid"]:
            return {"passed": False, "migration": migration, "audit": audit}
        return {
            "passed": True,
            "migration": migration,
            "audit": audit,
            "index": update(settings, verify_hashes=True),
            "utility": persist_scores(settings),
        }
    if args.command == "benchmark":
        return run_benchmark(
            settings, args.dataset, top_k=args.top_k, max_p95_ms=args.max_p95_ms
        )
    if args.command == "backup":
        return backup(settings)
    raise ESBError(f"Unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    try:
        result = dispatch(_parser().parse_args(argv))
        if result is not None:
            _json(result)
        if isinstance(result, dict) and result.get("valid") is False:
            return 1
        if isinstance(result, dict) and result.get("passed") is False:
            return 1
        return 0
    except (ESBError, ValueError, FileNotFoundError, PermissionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
