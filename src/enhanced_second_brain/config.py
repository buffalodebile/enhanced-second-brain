from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import ConfigurationError

DEFAULT_TOML = """[vault]
path = "."

[retrieval]
max_results = 5

[usage.weights]
injected = 0.25
opened = 1.0
cited = 2.0

[maintenance]
reconcile_after_hours = 24
reconcile_after_turns = 50
archive_review_after_days = 30
backup_after_hours = 24

[archive]
inactive_days = 240
max_effective_usage = 3.0
minimum_age_days = 60
cold_threshold = 0.15
minimum_backlinks = 2

[backup]
enabled = false
remote = "origin"
main_branch = "main"
snapshot_branch = "backup-snapshot"

"""


@dataclass(frozen=True)
class UsageConfig:
    weights: dict[str, float] = field(
        default_factory=lambda: {"injected": 0.25, "opened": 1.0, "cited": 2.0}
    )


@dataclass(frozen=True)
class ArchiveConfig:
    inactive_days: int = 240
    max_effective_usage: float = 3.0
    minimum_age_days: int = 60
    cold_threshold: float = 0.15
    minimum_backlinks: int = 2


@dataclass(frozen=True)
class MaintenanceConfig:
    reconcile_after_hours: int = 24
    reconcile_after_turns: int = 50
    archive_review_after_days: int = 30
    backup_after_hours: int = 24


@dataclass(frozen=True)
class BackupConfig:
    enabled: bool = False
    remote: str = "origin"
    main_branch: str = "main"
    snapshot_branch: str = "backup-snapshot"


@dataclass(frozen=True)
class Settings:
    vault: Path
    config_file: Path | None
    max_results: int = 5
    usage: UsageConfig = field(default_factory=UsageConfig)
    maintenance: MaintenanceConfig = field(default_factory=MaintenanceConfig)
    archive: ArchiveConfig = field(default_factory=ArchiveConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)


def _nearest_config(start: Path) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        path = candidate / "second-brain.toml"
        if path.is_file():
            return path
    return None


def _read_toml(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _resolved_vault(raw: str | Path, base: Path) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def resolve_settings(
    vault: str | Path | None = None, start: Path | None = None
) -> Settings:
    """Resolve --vault, ESB_VAULT_PATH, then nearest second-brain.toml."""
    start = (start or Path.cwd()).resolve()
    locator_config = _nearest_config(start)
    locator_data = _read_toml(locator_config)
    configured = locator_data.get("vault", {}).get("path")
    env_vault = os.environ.get("ESB_VAULT_PATH")
    raw_vault = vault or env_vault or configured
    if raw_vault is None:
        raise ConfigurationError(
            "No vault configured. Pass --vault, set ESB_VAULT_PATH, or create second-brain.toml."
        )
    base = locator_config.parent if locator_config else start
    resolved = _resolved_vault(raw_vault, base)
    vault_config = resolved / "second-brain.toml"
    config_file = vault_config if vault_config.is_file() else locator_config
    data = _read_toml(config_file)

    retrieval = data.get("retrieval", {})
    weights = data.get("usage", {}).get("weights", {})
    maintenance = data.get("maintenance", {})
    archive = data.get("archive", {})
    backup = data.get("backup", {})
    defaults = UsageConfig().weights
    merged_weights = {
        name: float(weights.get(name, value)) for name, value in defaults.items()
    }
    return Settings(
        vault=resolved,
        config_file=config_file,
        max_results=int(retrieval.get("max_results", 5)),
        usage=UsageConfig(merged_weights),
        maintenance=MaintenanceConfig(
            reconcile_after_hours=int(
                maintenance.get("reconcile_after_hours", 24)
            ),
            reconcile_after_turns=int(
                maintenance.get("reconcile_after_turns", 50)
            ),
            archive_review_after_days=int(
                maintenance.get("archive_review_after_days", 30)
            ),
            backup_after_hours=int(maintenance.get("backup_after_hours", 24)),
        ),
        archive=ArchiveConfig(
            inactive_days=int(archive.get("inactive_days", 240)),
            max_effective_usage=float(archive.get("max_effective_usage", 3.0)),
            minimum_age_days=int(archive.get("minimum_age_days", 60)),
            cold_threshold=float(archive.get("cold_threshold", 0.15)),
            minimum_backlinks=int(archive.get("minimum_backlinks", 2)),
        ),
        backup=BackupConfig(
            enabled=bool(backup.get("enabled", False)),
            remote=str(backup.get("remote", "origin")),
            main_branch=str(backup.get("main_branch", "main")),
            snapshot_branch=str(backup.get("snapshot_branch", "backup-snapshot")),
        ),
    )


def ensure_vault(settings: Settings) -> Path:
    if not settings.vault.is_dir():
        raise ConfigurationError(f"Vault does not exist: {settings.vault}")
    return settings.vault
