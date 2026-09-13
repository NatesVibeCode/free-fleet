# Contributing to free-fleet

Thank you for your interest in contributing to `free-fleet`!

## Philosophy
`free-fleet` keeps its trust boundaries explicit:
1. SQLite owns task revisions, queue leases, attempt budgets, route observations, and receipts.
2. OpenCode is invoked through the normally installed CLI with model tools and MCP disabled.
3. Only observed-zero routes enter the zero-price ladder.
4. Closed input and output schemas reject undeclared fields.
5. Evidence must match one source slice at exact offsets.

## Development Setup

```bash
git clone https://github.com/NatesVibeCode/free-fleet.git
cd free-fleet

# Install dependencies in editable mode
pip install -e ".[dev]"

# Run test suite
pytest -v

# Check the shared free-fleet contract across the local sibling checkouts
python3 scripts/check_fleet_drift.py
```

Do not include credentials, customer data, provider responses containing private data, or local machine paths in issues, fixtures, commits, or receipts.

## Adding a New Provider
Providers implement `BaseProvider` in `free_fleet/providers/base.py` and implement `run_prompt(route_id, prompt, system_prompt, timeout_sec, session_id)`.
All new providers must include token usage, duration, and reported cost telemetry in their receipt dict.
