# Task 3.6 - Idempotency Validation

## Test 1: Rerun with unchanged inputs

First run produced 120 deduplicated events, watermark set to `2026-08-21T10:00:00`. Rerun immediately after, no source changes:

- All 3 files skipped (hash matched, no re-copy)
- API fetched 0 new records (nothing past the watermark)
- events.jsonl stayed at 120 lines, no duplicates
- Watermark unchanged

Confirms reruns don't duplicate data and correctly reuse the saved watermark.

## Test 2: Full rebuild from scratch

Deleted `state/` and `raw/` entirely, reran from nothing.

- 3 files re-ingested, manifest rebuilt with 3 entries
- API pagination ran 7 pages, stopped correctly at `has_more: false`
- 122 fetched, 2 duplicates removed, 120 written
- Watermark advanced to `2026-08-21T10:00:00`

Same final state as the original run — fully reproducible from a clean slate. The 2 removed duplicates match the two event_ids the API is documented to intentionally repeat, caught by code, not hardcoded knowledge.

---

# Task 3.7 - Failure Experiment

Stopped the API server, ran the pipeline.

**Result:**
```
[api] ERROR: Could not connect to API at http://127.0.0.1:8000/api/events. Is local_api_server.py running?
[api] ingestion failed: Could not connect to API at http://127.0.0.1:8000/api/events. Is local_api_server.py running?
```

Failed clearly with a readable message. Run log recorded `status: failed` with the error captured. `watermark_before` and `watermark_after` were identical, the watermark never advanced because `save_watermark()` is never reached before the connection succeeds.

Restarted the server, reran from scratch: reached the same final state as before (120 records, same watermark), confirming clean recovery.