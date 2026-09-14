"""Studio API tests over an ephemeral localhost server (stdlib only)."""
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from harness_fleet.catalog import PriceState, RouteCatalog
from harness_fleet.studio import StudioHandler


@pytest.fixture()
def server(tmp_path: Path):
    db_path = tmp_path / "studio.db"
    catalog = RouteCatalog(db_path=db_path)
    catalog.add_route(
        route_id="demo/fake",
        provider="demo",
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        enabled=True,
        price_state=PriceState.PRICE_OBSERVED_ZERO.value,
        verification_source="test",
    )
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), StudioHandler)
    httpd.workspace_root = str(tmp_path)
    httpd.db_path = str(db_path)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}", tmp_path
    httpd.shutdown()
    thread.join(timeout=5)


def _call(base, method, path, body=None):
    request = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def test_harnesses_lists_seven_equal_entries(server):
    base, _ = server
    status, payload = _call(base, "GET", "/api/harnesses")
    assert status == 200
    assert [h["name"] for h in payload["harnesses"]] == [
        "opencode", "claude", "codex", "cursor", "grok", "muse", "antigravity",
    ]
    assert all("available" in h and "binary" in h for h in payload["harnesses"])


def test_routes_and_presets(server):
    base, _ = server
    status, payload = _call(base, "GET", "/api/routes")
    assert status == 200
    assert "demo/fake" in {r["id"] for r in payload["routes"]}
    status, payload = _call(base, "GET", "/api/presets")
    assert status == 200
    assert "score" in payload["presets"]


def test_run_plan_with_trust_note_and_lineage(server):
    base, _ = server
    items = [
        {"item_id": "i1", "text": "The checkout button gave a 500 error and blocks purchases."},
        {"item_id": "i2", "text": "Fast shipping and recyclable packaging was appreciated."},
    ]
    status, payload = _call(base, "POST", "/api/runs", {"steps": [
        {"preset": "classify", "task": "studio-triage", "items": items,
         "routes": ["demo/fake"], "max_attempts": 10, "concurrency": 2},
        {"preset": "score", "task": "studio-score", "items": items,
         "routes": ["demo/fake"], "max_attempts": 10, "concurrency": 2,
         "allow_paid": True, "paid_note": "demo stands in for a trusted paid route"},
    ]})
    assert status == 200
    first, second = payload["steps"]
    assert first["status"] == "completed" and first["verified"] == 2
    assert second["status"] == "completed" and second["verified"] == 2
    assert second["allow_paid"] is True
    assert second["paid_note"] == "demo stands in for a trusted paid route"
    status, snapshot = _call(base, "GET", f"/api/runs/{second['run_id']}")
    assert status == 200
    assert snapshot["parent_run_id"] == first["run_id"]


def test_run_validation_is_fail_closed(server):
    base, _ = server
    status, _ = _call(base, "POST", "/api/runs", {"steps": []})
    assert status == 400
    status, _ = _call(base, "POST", "/api/runs", {"steps": [{"preset": "score"}]})
    assert status == 400
    status, _ = _call(base, "GET", "/api/runs/does-not-exist")
    assert status in (404, 500)
    status, _ = _call(base, "GET", "/api/nope")
    assert status == 404


def test_index_page_serves(server):
    import urllib.request as _urlopen

    base, _ = server
    with _urlopen.urlopen(base + "/", timeout=10) as response:
        assert response.status == 200
        assert "Harness Studio" in response.read().decode()
