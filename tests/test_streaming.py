import json

import pytest

from harness_fleet.engine import Engine
from harness_fleet.input_data import iter_input_items
from harness_fleet.models import TaskSpec
from harness_fleet.packer import iter_packed_batches
from harness_fleet.store import MAX_NON_COUNTING_RETRIES, HarnessStore


def test_json_array_input_is_lazy(tmp_path):
    path = tmp_path / "items.json"
    path.write_text(json.dumps([
        {"item_id": "first", "text": "first source"},
        {"not_an_input": True},
    ]), encoding="utf-8")

    stream = iter_input_items(path)
    assert next(stream).item_id == "first"


def test_packer_stops_at_one_bounded_batch():
    def records():
        yield {"item_id": "one", "text": "one source"}
        yield {"item_id": "two", "text": "two source"}
        raise AssertionError("the next batch should not be consumed yet")

    batch = next(iter_packed_batches(records(), batch_size=2))
    assert [item["item_id"] for item in batch["items"]] == ["one", "two"]


def _stream_task(batch_size=1):
    return TaskSpec(
        name="streaming-test",
        batch_size=batch_size,
        claims_schema={
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
            "additionalProperties": False,
        },
    )


def test_failed_one_shot_ingestion_rolls_back_run_and_batches(tmp_path):
    store = HarnessStore(tmp_path / "broken.db")

    def broken_source():
        yield {"item_id": "one", "text": "source one"}
        raise RuntimeError("source failed")

    with pytest.raises(RuntimeError, match="source failed"):
        Engine(_stream_task(), store=store).run_campaign(broken_source(), "broken-run", "input.jsonl")

    assert store.run_exists("broken-run") is False


def test_changed_replayable_source_rolls_back_ingestion(tmp_path):
    store = HarnessStore(tmp_path / "changed.db")
    calls = 0

    def changing_source():
        nonlocal calls
        calls += 1
        yield {"item_id": "one", "text": "source one"}
        if calls == 1:
            yield {"item_id": "two", "text": "source two"}

    with pytest.raises(ValueError, match="no batches were committed"):
        Engine(_stream_task(), store=store).run_campaign(
            changing_source(), "changed-run", "input.jsonl", raw_items_factory=changing_source
        )

    assert store.run_exists("changed-run") is False


def test_non_counting_rate_limit_retries_are_bounded(tmp_path):
    store = HarnessStore(tmp_path / "rate.db")
    task = _stream_task()
    revision = store.register_task(task)
    store.create_run("rate-run", revision, "input", "d" * 64, 1, 2, 1, "output")
    batch = next(iter_packed_batches([{"item_id": "one", "text": "source one"}], batch_size=1))
    store.enqueue_batches("rate-run", [batch], max_attempts_per_batch=1)

    for number in range(MAX_NON_COUNTING_RETRIES):
        lease = store.lease_batch("rate-run", f"worker-{number}")
        assert lease is not None
        store.release_lease("rate-run", lease["attempt_id"], f"worker-{number}", "429 rate limit")

    assert store.lease_batch("rate-run", "after-cap") is None
    snapshot = store.run_snapshot("rate-run")
    assert next(iter(snapshot["batches"].values()))["status"] == "failed"
    assert snapshot["attempts_used"] == 0
