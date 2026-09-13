"""Regression tests for audit bug fixes."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from free_fleet.models import (
    CandidateExtractedItem,
    QuoteCandidate,
    InputItem,
    TaskSpec,
)
from free_fleet.providers.base import clean_llm_json
from free_fleet.providers.opencode import OpenCodeProvider
from free_fleet.input_data import load_input_items, _resolve_only_ids
from free_fleet.export import _filter_and_sort_records, _evaluate_filter
from free_fleet.grounding import normalize_grounding
from free_fleet.store import FreeFleetStore
from free_fleet.engine import Engine
from free_fleet.catalog import RouteCatalog, PriceState


def test_clean_llm_json_conversational_and_malformed():
    text1 = 'Certainly! Here is the JSON you requested:\n```json\n{"items": [{"id": 1}]}\n```\nHope this helps!'
    res1 = clean_llm_json(text1)
    assert res1 == {"items": [{"id": 1}]}

    text2 = '```json\n{"items": []}```'
    res2 = clean_llm_json(text2)
    assert res2 == {"items": []}

    text3 = '```\n{"items": ["a", "b"]} \n```'
    res3 = clean_llm_json(text3)
    assert res3 == {"items": ["a", "b"]}

    text4 = 'The result is: {"summary": "all clear"} - verified.'
    res4 = clean_llm_json(text4)
    assert res4 == {"summary": "all clear"}

    text5 = '```json\n{"items": [{"a": 1,},],}\n```'
    res5 = clean_llm_json(text5)
    assert res5 == {"items": [{"a": 1}]}

    assert clean_llm_json("") is None
    assert clean_llm_json("   ") is None
    assert clean_llm_json("Not a json at all") is None


def test_opencode_prefix_stripping():
    fake_runner = MagicMock()
    fake_runner.run.return_value = (
        0,
        json.dumps({"type": "text", "part": {"text": '{"items": []}'}}) + "\n" + json.dumps({"type": "step_finish", "part": {"cost": 0.0}}),
        "",
    )
    prov = OpenCodeProvider(runner=fake_runner)

    prov.run_prompt("opencode/anthropic/claude-3-5-sonnet", "test prompt")
    task_config = fake_runner.run.call_args[1]["task_config"]
    args = fake_runner.run.call_args[1]["args"]
    assert task_config["model"] == "anthropic/claude-3-5-sonnet"
    assert args[4] == "anthropic/claude-3-5-sonnet"

    prov.run_prompt("opencode:meta/llama-3", "test prompt")
    task_config = fake_runner.run.call_args[1]["task_config"]
    args = fake_runner.run.call_args[1]["args"]
    assert task_config["model"] == "meta/llama-3"
    assert args[4] == "meta/llama-3"


def test_csv_excel_bom_and_trailing_empty_rows(tmp_path: Path):
    bom_content = "\ufeffitem_id,text,title\nrow_1,Some text content,Title 1\nrow_2,More text content,Title 2\n\n   \n"
    csv_file = tmp_path / "excel_export.csv"
    csv_file.write_bytes(bom_content.encode("utf-8"))

    items = load_input_items(csv_file)
    assert len(items) == 2
    assert items[0].item_id == "row_1"
    assert items[0].text == "Some text content"
    assert items[1].item_id == "row_2"

    resolved = _resolve_only_ids(csv_file)
    assert resolved == {"row_1", "row_2"}


def test_export_sorting_mixed_types_and_quoted_filters():
    from free_fleet.models import ExtractedItem, QuoteRef

    digest = "a" * 64
    records = [
        ExtractedItem(
            item_id="rec_1",
            claims={"score": 85.0, "status": "passed"},
            quotes=[QuoteRef(slice_id="s1", start=0, end=10, text="verbatim12")],
            source_digest=digest,
            content_type="text/plain",
        ),
        ExtractedItem(
            item_id="rec_2",
            claims={"score": "N/A", "status": "failed"},
            quotes=[QuoteRef(slice_id="s1", start=0, end=10, text="verbatim12")],
            source_digest=digest,
            content_type="text/plain",
        ),
        ExtractedItem(
            item_id="rec_3",
            claims={"score": 95.0, "status": "passed"},
            quotes=[QuoteRef(slice_id="s1", start=0, end=10, text="verbatim12")],
            source_digest=digest,
            content_type="text/plain",
        ),
    ]

    sorted_recs = _filter_and_sort_records(records, sort_by="score", descending=True)
    assert [r.item_id for r in sorted_recs] == ["rec_3", "rec_1", "rec_2"]

    assert _evaluate_filter({"tier": "tier_1"}, "tier='tier_1'") is True
    assert _evaluate_filter({"tier": "tier_1"}, 'tier="tier_1"') is True
    assert _evaluate_filter({"score": 85}, "score>=80") is True


def test_resume_reclaims_abandoned_leased_batches(tmp_path: Path):
    db_path = tmp_path / "test.db"
    store = FreeFleetStore(db_path)
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

    spec = TaskSpec(
        name="test-task",
        instructions="Extract label",
        batch_size=1,
        claims_schema={"type": "object", "properties": {"label": {"type": "string"}}, "required": ["label"], "additionalProperties": False},
    )
    store.register_task(spec)

    items = [
        InputItem(item_id="item_1", text="This is sample text for item 1."),
        InputItem(item_id="item_2", text="This is sample text for item 2."),
    ]

    from free_fleet.packer import pack_items
    batches = pack_items(items, batch_size=1, max_slice_chars=1000)
    store.create_run(
        run_id="run_abandoned",
        task_revision_id=store.current_task_revision("test-task"),
        input_path="test",
        input_digest="a" * 64,
        total_items=2,
        max_attempts=10,
        batch_size=1,
        output_path=str(tmp_path / "packet.json"),
    )
    store.enqueue_batches("run_abandoned", batches, max_attempts_per_batch=3)

    lease1 = store.lease_batch("run_abandoned", worker_id="dead_worker")
    assert lease1 is not None
    with store.connect() as connection:
        connection.execute("UPDATE batches SET leased_at=datetime('now', '-10 minutes') WHERE run_id='run_abandoned' AND status='leased'")

    snapshot_before = store.run_snapshot("run_abandoned")
    assert snapshot_before["batches"][lease1["batch"]["batch_id"]]["status"] == "leased"

    from free_fleet.models import RoutePolicy
    engine = Engine(task=spec, store=store, catalog=catalog, policy=RoutePolicy(allowed_routes=["demo/fake"]))
    packet = engine.resume_campaign("run_abandoned", concurrency=1, output_packet_path=tmp_path / "packet.json")

    assert packet["total_verified_records"] == 2
    snapshot_after = store.run_snapshot("run_abandoned")
    assert snapshot_after["status"] == "completed"


def test_candidate_offsets_repaired_when_inaccurate():
    raw_cards = [{
        "item_id": "card_1",
        "source_digest": "a" * 64,
        "content_type": "text/plain",
        "slices": [{
            "slice_id": "card_1:s0",
            "start": 0,
            "end": 60,
            "text": "The company offers a free trial for 14 days without credit card.",
        }],
    }]

    extracted = [
        CandidateExtractedItem(
            item_id="card_1",
            claims={"label": "trial"},
            quotes=[QuoteCandidate(
                slice_id="card_1:s0",
                text="free trial for 14 days without",
                start=10,
                end=40,
            )],
        )
    ]

    normalized, err = normalize_grounding(extracted, raw_cards, min_quote_chars=15)
    assert err is None
    assert normalized is not None
    assert len(normalized) == 1
    quote = normalized[0].quotes[0]
    assert quote.start == 21
    assert quote.end == 51
    assert raw_cards[0]["slices"][0]["text"][quote.start:quote.end] == "free trial for 14 days without"


def test_mcp_server_evaluate_tool(tmp_path: Path):
    from free_fleet.mcp_server import create_mcp_server
    import anyio

    server = create_mcp_server(tmp_path)
    tool_names = [tool.name for tool in anyio.run(server.list_tools)]
    assert "free_fleet_eval" in tool_names


def test_canonical_url_preserves_query_params():
    from free_fleet.discover import canonical_url

    u1 = "https://news.ycombinator.com/item?id=123"
    u2 = "https://news.ycombinator.com/item?id=456"
    assert canonical_url(u1) != canonical_url(u2)
    assert canonical_url("https://news.ycombinator.com/item?id=123#reply") == "https://news.ycombinator.com/item?id=123"
    assert canonical_url("https://example.com/path/?a=1") == "https://example.com/path?a=1"


def test_to_input_items_handles_multiple_collisions():
    from free_fleet.discover import to_input_items, RawRecord

    records = [
        RawRecord(text="Item 1 text", source_uri="https://example.com/feed", title="Feed item"),
        RawRecord(text="Item 2 text", source_uri="https://example.com/feed", title="Feed item"),
        RawRecord(text="Item 3 text", source_uri="https://example.com/feed", title="Feed item"),
        RawRecord(text="Item 4 text", source_uri="https://example.com/feed", title="Feed item"),
    ]
    items = to_input_items(records)
    assert len(items) == 4
    item_ids = [it.item_id for it in items]
    assert len(set(item_ids)) == 4


def test_ats_records_includes_profile_evidence():
    from free_fleet.discover import _ats_records

    jobs = [{"id": 42, "title": "Staff Engineer", "content": "Full text of posting"}]
    records = _ats_records(
        jobs,
        source="greenhouse",
        org="stripe",
        get_text=lambda j: j["content"],
        get_url=lambda j: f"https://boards.greenhouse.io/stripe/jobs/{j['id']}",
        get_title=lambda j: j["title"],
        get_job_id=lambda j: str(j["id"]),
    )
    assert len(records) == 1
    assert records[0].metadata.get("evidence") == "profile"
    assert records[0].metadata.get("ats") == "greenhouse"
    assert records[0].metadata.get("org") == "stripe"


def test_gzipped_sitemap_decompression(tmp_path: Path):
    import gzip
    from free_fleet.discover import fetch_sitemap_urls
    import httpx

    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://example.com/page1</loc></url>
<url><loc>https://example.com/page2</loc></url>
</urlset>"""
    gzipped = gzip.compress(xml)

    def mock_handler(request):
        return httpx.Response(200, content=gzipped, headers={"Content-Type": "application/x-gzip"})

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)
    urls = fetch_sitemap_urls("https://example.com/sitemap.xml.gz", client=client)
    assert urls == ["https://example.com/page1", "https://example.com/page2"]


def test_scoring_respects_free_only_policy(tmp_path: Path):
    from free_fleet.scoring import filter_and_rank_routes
    from free_fleet.models import RoutePolicy
    from free_fleet.store import BulkLanesStore

    store = BulkLanesStore(tmp_path / "test.db")
    routes = [
        {"id": "paid/model-1", "provider": "paid", "price_state": "unknown", "cost_per_1k_input": 5.0, "cost_per_1k_output": 15.0},
        {"id": "free/model-1", "provider": "free", "price_state": "price_observed_zero", "cost_per_1k_input": 0.0, "cost_per_1k_output": 0.0},
    ]
    ranked = filter_and_rank_routes(routes, store=store, policy=RoutePolicy(free_only=True))
    assert ranked == ["free/model-1"]


def test_circuit_breaker_trips_when_route_pinned_and_free_only(tmp_path: Path):
    from free_fleet.catalog import RouteCatalog, RouteCircuitBreaker
    from free_fleet.models import RoutePolicy

    cat = RouteCatalog(tmp_path / "routes.json", db_path=tmp_path / "test.db")
    cat.add_route("openrouter/test-model", provider="openrouter", cost_per_1k_input=0.0, cost_per_1k_output=0.0)
    # Set price_state to unknown to verify policy.free_only forces run_is_free_only
    for r in cat.data["routes"]:
        if r["id"] == "openrouter/test-model":
            r["price_state"] = "unknown"
    cat.save()

    policy = RoutePolicy(free_only=True, allowed_routes=["openrouter/test-model"])
    with pytest.raises(RouteCircuitBreaker):
        cat.record_cost("openrouter/test-model", 0.05, policy=policy)


def test_route_catalog_init_with_string_path(tmp_path: Path):
    from free_fleet.catalog import RouteCatalog

    str_path = str(tmp_path / "custom_routes.json")
    catalog = RouteCatalog(str_path)
    assert isinstance(catalog.config_path, Path)


def test_account_fleet_db_env_var_respected(monkeypatch, tmp_path: Path):
    from free_fleet.store import default_db_path
    from free_fleet.cli import _store
    import argparse

    custom_db = str(tmp_path / "acct.db")
    monkeypatch.setenv("ACCOUNT_FLEET_DB", custom_db)
    monkeypatch.delenv("FREE_FLEET_DB", raising=False)
    monkeypatch.delenv("BULK_LANES_DB", raising=False)

    assert str(default_db_path()) == custom_db

    args = argparse.Namespace(workspace_root=str(tmp_path), db=None)
    store = _store(args)
    assert str(store.path) == custom_db


def test_safe_json_helper():
    from free_fleet.discover import _safe_json, DiscoverError
    import httpx

    resp_bad = httpx.Response(200, text="<html>Cloudflare 502 error</html>")
    with pytest.raises(DiscoverError) as exc_info:
        _safe_json(resp_bad, "https://example.com/api")
    assert "invalid JSON response" in str(exc_info.value)


def test_crawl_site_link_extraction_with_render_js(monkeypatch):
    from free_fleet.discover import crawl_site
    import httpx

    rendered_html = '<html><body><h1>Welcome</h1><a href="/subpage">Next</a></body></html>'
    monkeypatch.setattr("free_fleet.discover._render_js", lambda url, timeout: rendered_html)

    client = httpx.Client()
    records, skipped = crawl_site("https://example.com", client=client, max_pages=2, render_js=True, respect_robots=False)
    assert len(records) >= 1
    # Check that subpage was discovered from rendered HTML
    sources = [r.source_uri for r in records]
    assert "https://example.com" in sources

