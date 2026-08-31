# Contributing

Create a focused branch, add tests for behavior changes, and run:

```bash
python -m pip install -e ".[dev]"
pytest
esb --vault examples/demo-vault okf audit
esb --vault examples/demo-vault benchmark examples/demo-vault/benchmark.json --max-p95-ms 1000
```

Never submit a real vault, telemetry ledger, personal identifier, credential, private URL, or absolute home path. Examples must remain fictional and portable across Windows, macOS, and Linux.
