"""Create the verified release ZIP around a PyInstaller onedir application."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path, PurePosixPath


def package(source: Path, output: Path) -> None:
    source = source.resolve()
    output = output.resolve()
    if not source.is_dir():
        raise ValueError(f"Application directory not found: {source}")
    if output.suffix.casefold() != ".zip":
        raise ValueError("Release bundle must use a .zip extension")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                relative = path.relative_to(source)
                archive.write(
                    path,
                    PurePosixPath("enhanced-second-brain", *relative.parts).as_posix(),
                )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package(args.source, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
