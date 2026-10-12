"""Exercise the distributed binary's capture contract in an isolated temporary vault."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix="esb-hook-smoke-") as temporary:
        vault = Path(temporary) / "Brain with spaces"
        environment = dict(os.environ, CODEX_HOME=str(Path(temporary) / "codex"),
                           CLAUDE_CONFIG_DIR=str(Path(temporary) / "claude"))
        def command(*args, payload=None):
            result = subprocess.run([executable, "--vault", str(vault), *args],
                                    input=json.dumps(payload) if payload is not None else None,
                                    capture_output=True, encoding="utf-8", check=True, env=environment)
            return json.loads(result.stdout)
        command("install", "--no-hooks")
        begin = command("hook", "run", "--provider", "generic", payload={
            "event": "begin", "session_id": "smoke", "event_id": "first", "prompt": "A lasting decision"})
        token = begin["turn_id"]
        event = {"event": "end", "session_id": "smoke", "turn_id": token}
        assert command("hook", "run", "--provider", "generic", payload=event)["action"] == "continue"
        proposal = Path(temporary) / "capture.json"
        proposal.write_text(json.dumps({"updates": [{"path": "concepts/decision.md", "expected_sha256": None,
                            "metadata": {"title": "Portable capture", "description": "A synthetic result"},
                            "body": "# Portable capture\n\nThe hook completed."}]}), encoding="utf-8")
        assert command("checkpoint", "complete", "--turn-id", token, "--input", str(proposal))["complete"]
        assert command("hook", "run", "--provider", "generic", payload=event)["action"] == "allow"
        assert command("okf", "audit")["valid"]
        assert command("page", "read", "concepts/decision.md")["sha256"]
        # Execute the actual installed command shapes without starting an agent
        # or modifying the machine's real native configurations/trust records.
        for provider in ("codex", "claude"):
            configured = command("hooks", "install", "--provider", provider)
            config_path = configured["providers"][provider]["config"]
            config = json.loads(Path(config_path).read_text(encoding="utf-8"))
            handler = config["hooks"]["UserPromptSubmit"][0]["hooks"][0]
            event = {"session_id": f"native-{provider}", "turn_id": "native-first", "event_id": "first",
                     "hook_event_name": "UserPromptSubmit", "prompt": "No durable novelty"}
            if "args" in handler:
                argv = [handler["command"], *handler["args"]]
                shell = False
            else:
                argv = handler.get("commandWindows", handler["command"]) if os.name == "nt" else handler["command"]
                shell = True
            result = subprocess.run(argv, shell=shell, input=json.dumps(event), capture_output=True,
                                    encoding="utf-8", env=environment, check=True)
            injected = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
            native_token = injected.split("capture turn: ", 1)[1].split(".", 1)[0]
            proposal.write_text('{"updates": []}', encoding="utf-8")
            assert command("checkpoint", "complete", "--turn-id", native_token, "--input", str(proposal))["complete"]
            command("hooks", "uninstall", "--provider", provider)
        print("Portable hook and checkpoint smoke passed")


if __name__ == "__main__":
    main()
