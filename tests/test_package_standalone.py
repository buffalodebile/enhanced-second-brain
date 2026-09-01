from __future__ import annotations

import sys
import zipfile
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from package_standalone import package


def test_release_bundle_has_one_portable_application_root(tmp_path: Path) -> None:
    source = tmp_path / "build" / "enhanced-second-brain"
    runtime = source / "_internal"
    runtime.mkdir(parents=True)
    (source / "enhanced-second-brain.exe").write_bytes(b"launcher")
    (runtime / "python-runtime.dll").write_bytes(b"runtime")
    output = tmp_path / "enhanced-second-brain-windows-x64.zip"

    package(source, output)

    with zipfile.ZipFile(output) as archive:
        assert archive.namelist() == [
            "enhanced-second-brain/_internal/python-runtime.dll",
            "enhanced-second-brain/enhanced-second-brain.exe",
        ]
