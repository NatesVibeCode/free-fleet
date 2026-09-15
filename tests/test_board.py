"""Tests for the read-only results board (harness_fleet.board)."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

import pytest

from harness_fleet.board import (
    BOARD_HTML_PATH,
    BoardHandler,
    build_board_payload,
    latest_run_id,
    list_runs,
)
from harness_fleet.catalog import PriceState, RouteCatalog
from harness_fleet.engine import Engine
from harness_fleet.models import RoutePolicy
from harness_fleet.store import HarnessStore
from harness_fleet.task import create_task_from_preset


def _partner_run(tmp_path: Path, run_id: str = "board-run") -> Path:
    """A real, verified partner run produced by the deterministic demo provider."""
    db = tmp_path / "state.db"
    store = HarnessStore(db)
    # Register the deterministic demo route exactly as `quickstart --demo` does.
    catalog = RouteCatalog(db_path=store.path)
    catalog.add_route(
        route_id="demo/fake",
        provider="demo",
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        enabled=True,
        price_state=PriceState.PRICE_OBSERVED_ZERO.value,
        verification_source="board test (deterministic)",
    )
    task = create_task_from_preset("partner_research", preset_name="partner-research")
    store.register_task(task)
    items = [
        {"item_id": "cloud_solutions.io", "text": "Cloud Solutions is a certified Snowflake implementation partner delivering Kafka migrations for fintech clients."},
        {"item_id": "northwind.example", "text": "Northwind resells SaaS licences and offers staff augmentation."},
        {"item_id": "tiny.example", "text": "Two-person design studio."},
    ]
    Engine(
        task=task,
        store=store,
        policy=RoutePolicy(allowed_routes=["demo/fake"], free_only=True),
    ).run_campaign(
        raw_items=items,
        run_id=run_id,
        input_path=str(tmp_path / "partners.csv"),
        concurrency=1,
        max_attempts=5,
        output_packet_path=tmp_path / "packet.json",
    )
    return db


def test_payload_is_schema_driven_and_never_invents_scores(tmp_path):
    db = _partner_run(tmp_path)
    payload = build_board_payload(db)

    assert payload["run"]["run_id"] == "board-run"
    assert payload["stats"]["records"] == 3
    # Labels come from the task's own schema, not a hardcoded partner vocabulary.
    assert {c["item_id"] for c in payload["checklist"]} == {
        "q1_target_stack", "q2_service_model", "q3_industry_verticals",
        "q4_geography_delivery", "q5_vendor_alliances", "q6_case_study_proof",
    }
    assert all(c["label"] and c["points"] > 0 for c in payload["checklist"])
    assert payload["checklist_total"] == 100
    assert {a["key"] for a in payload["attributes"]} >= {"target_stack", "service_model", "vendor_alliances"}

    for partner in payload["partners"]:
        score = partner["score"]
        # A score is either a real number or None; never a fabricated 0.
        assert score is None or (isinstance(score, (int, float)) and 0 <= score <= 100)
        # The score equals the checklist points actually earned.
        assert partner["earned_points"] == sum(
            points for item, points in partner["checklist_points"].items() if partner["checklist"][item]
        )
        if score is not None:
            assert abs(score - partner["earned_points"]) < 1e-6
        assert partner["provenance"]["route"] == "demo/fake"
        assert partner["provenance"]["cost"] == 0.0


def test_payload_reports_quotes_and_provenance(tmp_path):
    db = _partner_run(tmp_path)
    payload = build_board_payload(db)
    with_quotes = [p for p in payload["partners"] if p["quotes"]]
    assert with_quotes, "the demo provider always returns quotes"
    quote = with_quotes[0]["quotes"][0]
    assert isinstance(quote["text"], str) and quote["text"]
    assert isinstance(quote["supports"], list)
    assert payload["stats"]["quote_count"] == sum(len(p["quotes"]) for p in payload["partners"])
    assert payload["stats"]["routes"] == ["demo/fake"]
    assert payload["stats"]["cost_reported"] == 0.0


def test_unknown_run_and_empty_database_are_explained(tmp_path):
    db = _partner_run(tmp_path)
    with pytest.raises(KeyError):
        build_board_payload(db, "nope")
    empty = HarnessStore(tmp_path / "empty.db")
    with pytest.raises(ValueError, match="no runs yet"):
        latest_run_id(empty)
    assert list_runs(HarnessStore(db))[0]["run_id"] == "board-run"


def test_board_page_ships_with_the_package():
    assert BOARD_HTML_PATH.is_file()
    html = BOARD_HTML_PATH.read_text(encoding="utf-8")
    assert "read-only" in html.lower() or "view only" in html.lower()
    # The page must not imply it writes anything.
    for verb in ("fetch(\"/api/crm/record\"", "method: \"POST\""):
        assert verb not in html


def test_http_endpoints_and_host_guard(tmp_path):
    db = _partner_run(tmp_path)
    BoardHandler.db_path = db
    BoardHandler.run_id = None
    server = ThreadingHTTPServer(("127.0.0.1", 0), BoardHandler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with urlopen(f"http://127.0.0.1:{port}/", timeout=20) as response:
            assert response.status == 200
            assert "text/html" in response.headers.get("Content-Type", "")
            assert b"board" in response.read().lower()

        with urlopen(f"http://127.0.0.1:{port}/api/board", timeout=20) as response:
            payload = json.loads(response.read())
        assert payload["run"]["run_id"] == "board-run"
        assert len(payload["partners"]) == 3

        with urlopen(f"http://127.0.0.1:{port}/api/runs", timeout=20) as response:
            assert json.loads(response.read())["runs"][0]["run_id"] == "board-run"

        with pytest.raises(urllib.error.HTTPError) as missing:
            urlopen(f"http://127.0.0.1:{port}/api/nope", timeout=20)
        assert missing.value.code == 404

        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/board", headers={"Host": "evil.example"}
        )
        with pytest.raises(urllib.error.HTTPError) as blocked:
            urlopen(request, timeout=20)
        assert blocked.value.code == 403

        # Writes are not part of this surface at all.
        for path in ("/api/crm/record", "/api/board"):
            post = urllib.request.Request(
                f"http://127.0.0.1:{port}{path}", data=b"{}", method="POST",
                headers={"Content-Type": "application/json"},
            )
            with pytest.raises(urllib.error.HTTPError) as not_allowed:
                urlopen(post, timeout=20)
            assert not_allowed.value.code == 501
    finally:
        server.shutdown()
        server.server_close()


def test_cli_prints_the_payload_with_json(tmp_path, capsys):
    from harness_fleet import cli

    db = _partner_run(tmp_path)
    cli.cmd_board(type("A", (), {"db": str(db), "run_id": "board-run", "json": True})())
    payload = json.loads(capsys.readouterr().out)
    assert payload["run"]["run_id"] == "board-run"
    assert payload["stats"]["records"] == 3
