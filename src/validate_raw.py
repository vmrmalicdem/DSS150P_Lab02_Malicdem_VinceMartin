"""Starter validation checks for raw outputs."""
from pathlib import Path
import json
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'raw'
STATE = ROOT / 'state'


def check_expected_raw_files_exist():
    expected = [
        RAW / 'files' / 'customers.csv',
        RAW / 'files' / 'orders.json',
        RAW / 'files' / 'products.parquet',
        RAW / 'api' / 'events.jsonl',
    ]
    for path in expected:
        assert path.exists(), f"expected raw output missing: {path}"
    print(f"[validate] all {len(expected)} expected raw files exist")


def load_api_events():
    events_path = RAW / 'api' / 'events.jsonl'
    events = []
    with events_path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def check_event_ids_unique(events):
    ids = [e['event_id'] for e in events]
    assert len(ids) == len(set(ids)), \
        f"duplicate event_id found in raw/api/events.jsonl ({len(ids)} rows, {len(set(ids))} unique)"
    print(f"[validate] event_id uniqueness OK ({len(ids)} records, all unique)")


def check_required_metadata_fields(events):
    required = ['event_id', 'customer_id', 'event_type', 'amount', 'updated_at', '_ingested_at', '_source']
    for e in events:
        for field in required:
            assert field in e and e[field] not in (None, ''), \
                f"record {e.get('event_id')} missing required field: {field}"
    print(f"[validate] required fields present on all {len(events)} records")


def check_updated_at_parseable(events):
    for e in events:
        raw_value = e['updated_at']
        try:
            datetime.fromisoformat(raw_value)
        except ValueError:
            raise AssertionError(
                f"record {e.get('event_id')} has unparseable updated_at: {raw_value!r}"
            )
    print(f"[validate] updated_at parses as a valid timestamp on all {len(events)} records")


def check_watermark_matches_max_updated_at(events):
    watermark_path = STATE / 'api_watermark.json'
    assert watermark_path.exists(), f"watermark file missing: {watermark_path}"

    watermark = json.loads(watermark_path.read_text())['updated_at']
    max_updated_at = max(e['updated_at'] for e in events)

    assert watermark == max_updated_at, (
        f"watermark ({watermark}) does not match max updated_at in raw output ({max_updated_at})"
    )
    print(f"[validate] watermark matches max updated_at: {watermark}")


def main():
    check_expected_raw_files_exist()

    events = load_api_events()
    check_event_ids_unique(events)
    check_required_metadata_fields(events)
    check_updated_at_parseable(events)
    check_watermark_matches_max_updated_at(events)

    print("[validate] all checks passed")


if __name__ == '__main__':
    main()