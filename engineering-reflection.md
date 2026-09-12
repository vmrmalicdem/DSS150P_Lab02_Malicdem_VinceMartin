# Engineering Reflection

**1. Why should source profiling occur before implementation of ingestion?**
I profile first so I understand what I'm building against before I build it. Skipping it means my logic breaks the moment it hits real messy data, like the duplicate customer IDs I found.

**2. What is the difference between source event time/updated_at and ingestion time?**
`updated_at` is when the record changed at the source. `_ingested_at` is when I actually pulled it. They can drift apart, especially after downtime.

**3. Why is event_id alone insufficient to decide which duplicate API record to keep in this exercise?**
`event_id` tells me which records are duplicates, not which one is current. I need `updated_at` too, to know which copy to keep.

**4. Why must watermark state advance only after successful persistence?**
If I save the watermark before the write succeeds and the write fails, I'll think that data was captured when it wasn't. It gets skipped forever with no warning.

**5. What limitation does updated_after > watermark have when multiple source records can share exactly the same timestamp?**
The check is strict greater-than. Any record sharing my exact watermark timestamp gets silently excluded on the next run.

**6. How is duplicate prevention related to idempotency?**
Idempotency means reruns give the same result. Without solid dedup, every rerun just piles on more copies of the same data.

**7. Why should the raw area preserve source values instead of applying business transformations?**
Raw data has to stay untouched so I can see exactly what the source sent. If I transform on the way in, bugs become permanent and unrecoverable.

**8. How could querying a production OLTP source for profiling or extraction degrade the application?**
Heavy queries against a live production table compete with real transactions for locks and I/O, which can slow down or block the actual application.

**9. What would you change if the API had a rate limit of 60 requests per minute?**
I'd add a delay between requests to stay under the limit, plus retry logic with backoff for any `429` responses.

**10. How would you extend this pipeline from a local raw area to PostgreSQL while preserving rerun safety?**
I'd switch to an upsert (`ON CONFLICT DO UPDATE`) so reruns update rows instead of duplicating them, and move the watermark into the database so it stays consistent with what it's tracking.