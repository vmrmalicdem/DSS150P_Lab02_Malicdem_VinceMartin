# Logical Schema

## customers

| Field | Logical Type | Nullable | Key Role | Definition |
|---|---|---|---|---|
| customer_id | String (ID) | No | Primary/candidate key | Unique identifier for a customer. Source data currently violates uniqueness (250 rows, 247 unique values, including one ID with conflicting attributes) - this is the intended key, not a currently-enforced one. |
| first_name | String | No | — | Customer's given name |
| last_name | String | No | — | Customer's family name |
| email | String | Yes | — | Customer's contact email address (3 missing in source) |
| city | String | Yes | — | Customer's city of residence (2 missing in source) |
| signup_date | Date | No | — | Date the customer registered. Arrives as plain text in the CSV; logically a date, not a string. |
| customer_segment | String (categorical) | No | — | Business classification of the customer (e.g. Student, Professional, SME, Retail) |

## API events

| Field | Logical Type | Nullable | Key Role | Definition |
|---|---|---|---|---|
| event_id | String (ID) | No | Primary/candidate key | Unique identifier for an event |
| customer_id | String | No | Foreign key (references customers) | Identifies which customer the event belongs to |
| event_type | String (categorical) | No | — | Category of event (e.g. page_view) |
| amount | Float | No | — | Monetary or numeric value associated with the event |
| updated_at | Timestamp | No | Watermark field | Last modification time of the record. Arrives as ISO-8601 text; logically a timestamp. Used as the incremental watermark for ingestion. |
| metadata | Object (nested) | No | — | Additional contextual attributes (channel, campaign). Could be flattened into columns or kept as a related sub-table downstream. |

## Source representation vs. logical type

Both `customers.signup_date` and `events.updated_at` arrive as plain text in their source formats (CSV and JSON respectively), but their intended logical type is date/timestamp. Any transformation layer consuming these fields must parse them explicitly; they do not arrive correctly typed on their own.

`customer_id` is defined here as the primary key by design intent, but the actual source data does not currently satisfy that constraint. This gap between intended schema and observed data is itself a documented quality issue (see source metadata inventory) and would need a resolution rule (e.g. dedup logic, a data steward decision on which record wins) before `customer_id` can be enforced as a hard key downstream.