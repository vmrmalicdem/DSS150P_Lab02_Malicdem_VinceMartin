# Terminal Transcript

Evidence for: PostgreSQL inspection, paginated API retrieval, first ingestion run, idempotent rerun, and failed-then-recovered API run.

---

## 1. PostgreSQL Inspection

```
DROP TABLE
CREATE TABLE
INSERT 0 250
 row_count
-----------
       250
(1 row)

 ticket_id | customer_id | category  | priority | assigned_agent |      opened_at      |     resolved_at     |   status
-----------+-------------+-----------+----------+----------------+---------------------+---------------------+-------------
         1 | C0246       | Technical | High     | J. Reyes       | 2026-06-19 04:00:00 | 2026-06-21 13:00:00 | Resolved
         2 | C0130       | Product   | Medium   | J. Reyes       | 2026-05-26 07:00:00 | 2026-05-26 23:00:00 | Closed
         3 | C0094       | Delivery  | Medium   | J. Reyes       | 2026-03-28 09:00:00 | 2026-03-31 17:00:00 | Closed
         4 | C0057       | Technical | High     | L. Tan         | 2026-04-25 19:00:00 |                     | In Progress
         5 | C0120       | Delivery  | High     | R. Cruz        | 2026-01-20 02:00:00 | 2026-01-22 21:00:00 | Resolved
         6 | C0211       | Product   | Medium   | P. Lim         | 2026-02-26 13:00:00 |                     | Open
         7 | C0041       | Delivery  | Low      | P. Lim         | 2026-03-11 23:00:00 |                     | Open
         8 | C0040       | Billing   | Low      | L. Tan         | 2026-02-14 05:00:00 | 2026-02-16 08:00:00 | Resolved
         9 | C0155       | Technical | Low      | R. Cruz        | 2026-02-09 04:00:00 | 2026-02-11 08:00:00 | Resolved
        10 | C0094       | Account   | Low      | J. Reyes       | 2026-04-12 19:00:00 |                     | In Progress
(10 rows)

 unassigned_tickets
--------------------
                  4
(1 row)

 category  | tickets
-----------+---------
 Account   |      60
 Product   |      51
 Delivery  |      49
 Billing   |      47
 Technical |      43
(5 rows)
```

```
                Table "public.support_tickets"
     Column     |            Type             | Nullable
-----------------+------------------------------+----------
 ...              ...                          | not null
 category        | character varying(40)       | not null
 priority        | character varying(10)       | not null
 assigned_agent  | character varying(80)       |
 opened_at       | timestamp without time zone | not null
 resolved_at     | timestamp without time zone |
 status          | character varying(20)       | not null
Indexes:
    "support_tickets_pkey" PRIMARY KEY, btree (ticket_id)
```

---

## 2. Paginated API Retrieval

```
Page 1 response keys: ['page', 'per_page', 'total', 'has_more', 'next_page', 'items']
page: 1
per_page: 10
total: 122
has_more: True
next_page: 2
items in this page: 10

First item fields:
  event_id: str = E0001
  customer_id: str = C0024
  event_type: str = page_view
  amount: float = 4210.54
  updated_at: str = 2026-08-01T11:00:00
  metadata: dict = {'channel': 'partner', 'campaign': 'none'}

Page 2 has_more: True, items: 10
```

---

## 3. First Ingestion Run (full rebuild from scratch)

```
[files] INGESTED customers.csv -> raw\files\customers.csv (18183 bytes)
[files] INGESTED orders.json -> raw\files\orders.json (77938 bytes)
[files] INGESTED products.parquet -> raw\files\products.parquet (14652 bytes)
[files] manifest written: state\files_manifest.json (3 total entries)
[api] page 1: 20 items, has_more=True
[api] page 2: 20 items, has_more=True
[api] page 3: 20 items, has_more=True
[api] page 4: 20 items, has_more=True
[api] page 5: 20 items, has_more=True
[api] page 6: 20 items, has_more=True
[api] page 7: 2 items, has_more=False
[api] fetched 122 new/updated records total
[api] wrote 120 deduplicated records to raw\api\events.jsonl
[api] 2 duplicate record(s) removed during dedup
[api] watermark advanced to 2026-08-21T10:00:00
```

---

## 4. Idempotent Rerun (unchanged inputs, with validation)

```
[files] SKIP customers.csv - unchanged (sha256 matches last ingest)
[files] SKIP orders.json - unchanged (sha256 matches last ingest)
[files] SKIP products.parquet - unchanged (sha256 matches last ingest)
[files] manifest written: state\files_manifest.json (3 total entries)
[files] validation passed: 3 manifest entries checked
[api] starting from watermark: 2026-08-21T10:00:00
[api] page 1: 0 items, has_more=False
[api] fetched 0 new/updated records total
[api] wrote 120 deduplicated records to raw\api\events.jsonl
[api] 0 duplicate record(s) removed during dedup
[api] validation passed: 120 records checked, all unique event_id
[api] no new records fetched; watermark unchanged
```

**Standalone validation confirmation (validate_raw.py):**
```
[validate] all 4 expected raw files exist
[validate] event_id uniqueness OK (120 records, all unique)
[validate] required fields present on all 120 records
[validate] updated_at parses as a valid timestamp on all 120 records
[validate] watermark matches max updated_at: 2026-08-21T10:00:00
[validate] all checks passed
```

---

## 5. Failed-then-Recovered API Run

**Failure (API server stopped):**
```
[files] SKIP customers.csv - unchanged (sha256 matches last ingest)
[files] SKIP orders.json - unchanged (sha256 matches last ingest)
[files] SKIP products.parquet - unchanged (sha256 matches last ingest)
[files] manifest written: state\files_manifest.json (6 total entries)
[api] starting from watermark: 2026-08-21T10:00:00
[api] ERROR: Could not connect to API at http://127.0.0.1:8000/api/events. Is local_api_server.py running?
[api] ingestion failed: Could not connect to API at http://127.0.0.1:8000/api/events. Is local_api_server.py running?
```

Run log row for this attempt (from `outputs/pipeline_run_log.csv`):
```
dd010988-86e1-49ed-89a4-a053530d1fe3,2026-09-12T07:41:51.714509+00:00,2026-09-12T07:41:53.755531+00:00,failed,api,0,0,0,2026-08-21T10:00:00,2026-08-21T10:00:00,Could not connect to API at http://127.0.0.1:8000/api/events. Is local_api_server.py running?
```
Note: watermark_before and watermark_after are identical, confirming the watermark did not advance on failure.

**Recovery (server restarted, pipeline rerun, full rebuild from scratch to prove reproducibility):**
```
[files] INGESTED customers.csv -> raw\files\customers.csv (18183 bytes)
[files] INGESTED orders.json -> raw\files\orders.json (77938 bytes)
[files] INGESTED products.parquet -> raw\files\products.parquet (14652 bytes)
[files] manifest written: state\files_manifest.json (3 total entries)
[api] page 1: 20 items, has_more=True
[api] page 2: 20 items, has_more=True
[api] page 3: 20 items, has_more=True
[api] page 4: 20 items, has_more=True
[api] page 5: 20 items, has_more=True
[api] page 6: 20 items, has_more=True
[api] page 7: 2 items, has_more=False
[api] fetched 122 new/updated records total
[api] wrote 120 deduplicated records to raw\api\events.jsonl
[api] 2 duplicate record(s) removed during dedup
[api] watermark advanced to 2026-08-21T10:00:00
```

Recovery reached the identical final state as the original first run (120 records, same watermark), confirming full reproducibility after failure.