"""Measure idle Stop, validated capture and optional portable process startup."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

from enhanced_second_brain import __version__, checkpoints, hooks
from enhanced_second_brain.atomic import write_json
from enhanced_second_brain.config import Settings
from enhanced_second_brain.index import rebuild
from enhanced_second_brain.okf import migrate_vault

from benchmark_comparison import percentile, write_test_vault


def measure(action, repeats):
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        action()
        samples.append((time.perf_counter() - start) * 1000)
    return {"median_ms": round(statistics.median(samples), 3), "p95_ms": round(percentile(samples, 95), 3), "samples": repeats}


def run(pages, repeats, executable=None):
    with tempfile.TemporaryDirectory(prefix="esb-hook-benchmark-") as directory:
        vault = Path(directory) / "vault"
        write_test_vault(vault, pages)
        migrate_vault(vault, write=True)
        settings = Settings(vault=vault, config_file=None)
        rebuild(settings)
        token = "benchmark-idle"
        write_json(checkpoints.turn_path(settings, token), {"turn_id": token, "session_key": checkpoints.digest("generic:benchmark"), "status": "complete"})
        write_json(hooks._session_path(settings, "generic", "benchmark"), {"current": token})
        event = {"session_id": "benchmark", "event": "end", "turn_id": token}
        hooks.run(settings, "generic", event)
        idle = measure(lambda: hooks.run(settings, "generic", event), repeats)
        number = 0
        def capture():
            nonlocal number
            number += 1
            current = f"capture-{number}"
            write_json(checkpoints.turn_path(settings, current), {"turn_id": current, "status": "open"})
            checkpoints.complete(settings, current, {"updates": [{
                "path": f"concepts/capture-{number}.md", "expected_sha256": None,
                "metadata": {"title": f"Capture {number}", "description": "Verified synthetic result"},
                "body": "# Capture\n\nA synthetic durable result.",
            }]})
        dirty = measure(capture, repeats)
        report = {"pages": pages, "idle_stop": idle, "one_page_capture": dirty,
                  "idle_engine_target_passed": idle["p95_ms"] < 20}
        if executable:
            def external():
                result = subprocess.run([str(executable), "--vault", str(vault), "hook", "run", "--provider", "generic"],
                                        input=json.dumps(event), encoding="utf-8", capture_output=True, check=True)
                assert json.loads(result.stdout)["action"] == "allow"
            external()
            report["portable_idle_process"] = measure(external, repeats)
            report["portable_target_passed"] = report["portable_idle_process"]["p95_ms"] < 500
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, nargs="+", default=[500, 2500])
    parser.add_argument("--repeats", type=int, default=30)
    parser.add_argument("--executable", type=Path)
    args = parser.parse_args()
    print(json.dumps({"version": __version__, "platform": platform.platform(), "python": platform.python_version(),
                      "results": [run(count, args.repeats, args.executable) for count in args.pages]}, indent=2))


if __name__ == "__main__":
    main()
