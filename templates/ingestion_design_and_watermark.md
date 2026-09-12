# Task 2.4 - Ingestion Design Justification

| Source | Method | Raw Destination | Duplicate Key | Incremental State |
|---|---|---|---|---|
| CSV/JSON/Parquet | File copy + manifest | `raw/files/` | File SHA-256 | N/A |
| REST API | Paginated GET | `raw/api/events.jsonl` | `event_id` | `max(updated_at)` |
| PostgreSQL | Inspection only in this lab | N/A | `ticket_id` | Discuss possible timestamp/CDC strategy |

**CSV/JSON/Parquet - file copy + SHA-256:** These files have no change-tracking field. Hashing the content is the only reliable way to detect whether a file was already ingested; filenames and mod-times can be misleading.

**REST API - pagination + event_id dedup + updated_at watermark:** `per_page` caps results below `total`, so pagination is required to get complete data. The API supports `updated_after`, so it's built for incremental pulls. The source reissues existing `event_id`s with newer `updated_at` values, so dedup must keep the latest version per ID, not treat repeats as new rows.

**PostgreSQL - inspection only:** Lab scope is limited to profiling, per the constraint against loading source systems unnecessarily. Production equivalent: a `last_modified` column with polling, or CDC tooling (e.g. Debezium) for log-based capture.

---

# Task 2.5 - Watermark Semantics

**If the watermark saves before the raw write succeeds:** A failed or crashed write after the watermark advances means the next run skips those records permanently, thinking they're already captured. Silent data loss, no error raised.

**If the source allows duplicate timestamps:** The comparison is strict `updated_at > watermark`. Any record sharing the exact watermark timestamp gets excluded forever on future runs, since it can never satisfy `>`.

**Limitation:** No tie-breaking for same-timestamp records. Assumes the source clock is monotonic; a late backfill with an older timestamp is never picked up once the watermark has passed it.

**Mitigation:** Use a composite `(updated_at, event_id)` watermark to break ties, or replace the timestamp entirely with a strictly increasing cursor (sequence number, CDC log position).