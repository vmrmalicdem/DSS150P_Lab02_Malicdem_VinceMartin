# Source Profiling Report

## 1. Source Inventory

| Source | Type | Rows/Records | Key | Update Pattern | Quality Findings |
|---|---|---:|---|---|---|
| customers.csv | CSV file | 250 | customer_id (not unique) | Static file | 3 missing emails, 2 missing cities, 4 duplicate rows, 247 unique IDs out of 250 |
| orders.json | JSON file | 250 | order_id | Static file | No missing values; timestamps stored as text |
| products.parquet | Parquet file | 200 | product_id | Static file | No missing values; types preserved natively |
| REST API - events | Paginated API | 122 raw, 120 after dedup | event_id | Incremental (updated_after) | 2 event_ids intentionally repeated with newer timestamps |
| support_tickets | PostgreSQL table | 250 | ticket_id | Static seed here; live in production | 4 NULL assigned_agent; resolved_at NULL when status is Open/In Progress |

## 2. Schema Findings

- **customers.csv**: 7 text columns (customer_id, first_name, last_name, email, city, signup_date, customer_segment). `signup_date` is text but logically a date.
- **orders.json**: 9 fields including a nested `shipping` object (region, method). All 250 records share the same keys. `order_timestamp` is text, logically a timestamp.
- **products.parquet**: 7 columns, types preserved on read (float64, int32) unlike CSV/JSON, which need re-inference.
- **REST API events**: event_id, customer_id, event_type, amount (float), updated_at (text), nested metadata (channel, campaign).
- **support_tickets**: 8 columns — ticket_id (integer, primary key), customer_id (varchar 10), category (varchar 40), priority (varchar 10), assigned_agent (varchar 80, nullable), opened_at (timestamp), resolved_at (timestamp, nullable), status (varchar 20).

## 3. Data Quality Findings

1. customers.csv: 4 exact duplicate rows.
2. customers.csv: customer_id not unique (250 rows, 247 unique values). One case (C0090) is a real key collision with conflicting data, not just a duplicate.
3. customers.csv: 3 missing emails, 2 missing cities.
4. REST API: 2 event_ids deliberately repeated with newer updated_at values.
5. support_tickets: 4 unassigned tickets. resolved_at is NULL exactly when status is Open/In Progress — expected, not a defect, but must be handled downstream.
6. Timestamps arrive as plain text everywhere except Parquet, which is the only source with native typing.

## 4. Recommended Acquisition Method

| Source | Method | Why |
|---|---|---|
| CSV/JSON/Parquet | File copy + SHA-256 manifest | No change-tracking field; hashing is the only reliable way to detect an already-ingested file |
| REST API | Paginated GET, incremental via updated_after, dedup by event_id keeping latest updated_at | Supports incremental filtering; caps results per page; reissues IDs with newer data |
| support_tickets | Bounded inspection only (this lab) | Scope excludes building a live pipeline against this source; production would use a timestamp column with polling or CDC |

## 5. Risks and Assumptions

- customer_id is assumed to be a clean key downstream, but the source violates that now. Needs a dedup/survivorship rule before enforcing uniqueness.
- Text-based timestamps are assumed to parse cleanly; not fully validated.
- The watermark assumes updated_at is monotonic with no exact-timestamp collisions at the boundary; a collision there could silently drop a record.
- support_tickets was only read-only profiled here; no assumptions carry over to a live incremental pattern.
- Nested objects (shipping, metadata) are assumed structurally stable; not validated against future source changes.