from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from . import __version__
from .backup import SECRET_NAME
from .config import Settings, resolve_settings
from .errors import SafetyError, ValidationError
from .index import rebuild
from .okf import audit_vault

BUNDLE_FORMAT = "enhanced-second-brain"
BUNDLE_VERSION = 1
MANIFEST_NAME = "enhanced-second-brain-bundle.json"
WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}

EXCLUDED_DIRECTORIES = {
    ".git",
    ".obsidian",
    "_meta/cache",
    "_archives/install-preflight",
}
EXCLUDED_FILES = {
    ".gitignore",
    ".ds_store",
    "thumbs.db",
    "agents.md",
    "claude.md",
    "_meta/usage.jsonl.lock",
    "_meta/utility.json",
    MANIFEST_NAME,
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _archive_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_excluded(relative: str) -> bool:
    comparable = relative.lower()
    if comparable in EXCLUDED_FILES:
        return True
    return any(
        comparable == directory or comparable.startswith(f"{directory}/")
        for directory in EXCLUDED_DIRECTORIES
    )


def _bundle_files(vault: Path) -> list[tuple[str, bytes]]:
    selected: list[tuple[str, bytes]] = []
    blocked: list[str] = []
    portable_names: set[str] = set()
    for path in sorted(vault.rglob("*")):
        if path.is_symlink():
            relative = PurePosixPath(path.relative_to(vault)).as_posix()
            if not _is_excluded(relative):
                blocked.append(f"{relative} (symbolic link)")
            continue
        if not path.is_file():
            continue
        relative = PurePosixPath(path.relative_to(vault)).as_posix()
        if _is_excluded(relative):
            continue
        try:
            _safe_member(relative)
        except SafetyError:
            blocked.append(f"{relative} (non-portable path)")
            continue
        comparable = relative.casefold()
        if comparable in portable_names:
            blocked.append(f"{relative} (case-insensitive path collision)")
            continue
        portable_names.add(comparable)
        if SECRET_NAME.search(path.name):
            blocked.append(f"{relative} (secret-like filename)")
            continue
        selected.append((relative, path.read_bytes()))
    if blocked:
        raise SafetyError("Portable export refused: " + ", ".join(blocked))
    return selected


def _resolved_output(vault: Path, raw: str | Path) -> Path:
    output = Path(raw).expanduser()
    if output.exists() and output.is_dir():
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        output = output / f"enhanced-second-brain-{stamp}.zip"
    elif output.suffix.lower() != ".zip":
        output = output.with_suffix(".zip")
    output = output.resolve()
    try:
        output.relative_to(vault.resolve())
    except ValueError:
        pass
    else:
        raise SafetyError("Export destination must be outside the vault")
    if output.exists():
        raise SafetyError(f"Export destination already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def export_bundle(settings: Settings, destination: str | Path) -> dict[str, Any]:
    audit = audit_vault(settings.vault, strict=True)
    if not audit["valid"]:
        raise ValidationError("Strict OKF audit failed; refusing portable export")
    output = _resolved_output(settings.vault, destination)
    files = _bundle_files(settings.vault)
    manifest = {
        "format": BUNDLE_FORMAT,
        "format_version": BUNDLE_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "tool_version": __version__,
        "files": [
            {"path": relative, "size": len(data), "sha256": _sha256(data)}
            for relative, data in files
        ],
    }
    descriptor = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode(
            "utf-8"
        )
        + b"\n"
    )
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".esb-export-", suffix=".zip", dir=output.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            archive.writestr(MANIFEST_NAME, descriptor)
            for relative, data in files:
                archive.writestr(relative, data)
        os.replace(temporary, output)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {
        "bundle": str(output),
        "sha256": _archive_sha256(output),
        "files": len(files),
        "knowledge_pages": sum(
            1 for relative, _ in files if relative.lower().endswith(".md")
        ),
        "bytes": output.stat().st_size,
        "verified": True,
    }


def _safe_member(raw: str) -> str:
    if not raw or "\\" in raw:
        raise SafetyError(f"Unsafe bundle path: {raw!r}")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts:
        raise SafetyError(f"Unsafe bundle path: {raw!r}")
    for part in path.parts:
        stem = part.split(".", 1)[0].casefold()
        if (
            any(ord(character) < 32 or character in '<>:"|?*' for character in part)
            or part.endswith((" ", "."))
            or stem in WINDOWS_RESERVED_NAMES
        ):
            raise SafetyError(f"Non-portable bundle path: {raw!r}")
    normalized = path.as_posix()
    if normalized in {"", ".", MANIFEST_NAME}:
        raise SafetyError(f"Unsafe bundle path: {raw!r}")
    if _is_excluded(normalized):
        raise SafetyError(f"Machine-specific bundle path refused: {raw!r}")
    return normalized


def _read_manifest(archive: zipfile.ZipFile) -> dict[str, Any]:
    names = archive.namelist()
    if names.count(MANIFEST_NAME) != 1:
        raise ValidationError("Bundle manifest is missing or duplicated")
    try:
        manifest = json.loads(archive.read(MANIFEST_NAME))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValidationError("Bundle manifest is not valid UTF-8 JSON") from exc
    if (
        not isinstance(manifest, dict)
        or manifest.get("format") != BUNDLE_FORMAT
        or manifest.get("format_version") != BUNDLE_VERSION
        or not isinstance(manifest.get("files"), list)
    ):
        raise ValidationError("Unsupported Enhanced Second Brain bundle")
    return manifest


def _verified_entries(
    archive: zipfile.ZipFile, manifest: dict[str, Any]
) -> list[tuple[str, bytes]]:
    entries: list[tuple[str, bytes]] = []
    expected: set[str] = set()
    portable_names: set[str] = set()
    for item in manifest["files"]:
        if not isinstance(item, dict):
            raise ValidationError("Invalid file entry in bundle manifest")
        relative = _safe_member(str(item.get("path", "")))
        if relative in expected:
            raise ValidationError(f"Duplicate bundle path: {relative}")
        comparable = relative.casefold()
        if comparable in portable_names:
            raise ValidationError(f"Case-insensitive bundle path collision: {relative}")
        portable_names.add(comparable)
        if archive.namelist().count(relative) != 1:
            raise ValidationError(f"Duplicate ZIP member: {relative}")
        expected.add(relative)
        try:
            data = archive.read(relative)
            size = int(item["size"])
            digest = str(item["sha256"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError(f"Invalid manifest values for {relative}") from exc
        if len(data) != size or _sha256(data) != digest:
            raise ValidationError(f"Bundle checksum mismatch: {relative}")
        entries.append((relative, data))
    actual = {name for name in archive.namelist() if name != MANIFEST_NAME}
    if actual != expected:
        raise ValidationError("Bundle content does not match its manifest")
    return entries


def restore_bundle(bundle: str | Path, destination: str | Path) -> dict[str, Any]:
    source = Path(bundle).expanduser().resolve(strict=True)
    target = Path(destination).expanduser().resolve()
    if target.exists():
        raise SafetyError(f"Restore destination must not exist: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = Path(
        tempfile.mkdtemp(prefix=".esb-restore-", dir=target.parent)
    )
    try:
        try:
            with zipfile.ZipFile(source, "r") as archive:
                manifest = _read_manifest(archive)
                entries = _verified_entries(archive, manifest)
        except zipfile.BadZipFile as exc:
            raise ValidationError("Portable bundle is not a valid ZIP file") from exc
        for relative, data in entries:
            path = temporary.joinpath(*PurePosixPath(relative).parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        audit = audit_vault(temporary, strict=True)
        if not audit["valid"]:
            raise ValidationError("Restored knowledge failed the strict OKF audit")
        os.replace(temporary, target)
        temporary = None
        settings = resolve_settings(target)
        index = rebuild(settings)
        return {
            "vault": str(target),
            "source": str(source),
            "files": len(entries),
            "audit": audit,
            "index": index,
            "verified": True,
            "next_step": (
                "Run install for this vault so the local agent instructions and "
                "automatic maintenance are regenerated for this machine."
            ),
        }
    finally:
        if temporary is not None and temporary.exists():
            shutil.rmtree(temporary)
