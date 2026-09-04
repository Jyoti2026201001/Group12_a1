# StaySpot — Assignment 1 (Project 3: Vacation Rental & Experiences)

CS6.302 - Software System Development | Team: Group 12

## 1. Project

**StaySpot** is a vacation-rental platform. This repo implements the database layer only
(no application/front-end code), split across:

- **PostgreSQL** — transactional core: guests, wallets, properties, bookings, audit trail.
- **MongoDB** — flexible/high-volume data: property amenities, reviews, and geospatial
  "search hotspot" pings.

## 2. Repository structure

```text
README.md

docs/
  relational__erd.png        # PostgreSQL schema ERD
  mongo_schema_map.json      # MongoDB collection field/validator map

sql/
  01_schema_ddl.sql          # guests, wallet_audit_logs, properties, bookings
  02_indexes.sql             # partial unique index + secondary indexes
  03_triggers_and_audit.sql  # wallet audit trigger
  04_stored_procedures.sql   # sp_atomic_booking (Workflow 1)
  05_materialized_views.sql  # property_summary + refresh function
  06_window_analytics.sql    # Workflow 2: 7-day moving average + DENSE_RANK

mongo/
  01_collections_and_indexes.js  # collections, JSON Schema validators, indexes
  02_workflow3_geonear.js        # Workflow 3: $geoNear trending hotspots
  03_workflow4_facet.js          # Workflow 4: $facet review analytics

data_generation/
  postgres_seeder.py         # seeds guests, properties, bookings, wallet audit
  mongo_seeder.py            # seeds amenities, reviews, search sessions
  requirements.txt

performance/
  postgres_explain_analyzes.txt   # currently a placeholder — see Section 8
  mongo_execution_stats.json      # currently a placeholder — see Section 8
```

## 3. PostgreSQL setup

```bash
createdb stayspot
psql -d stayspot -f sql/01_schema_ddl.sql
psql -d stayspot -f sql/02_indexes.sql
psql -d stayspot -f sql/03_triggers_and_audit.sql
psql -d stayspot -f sql/04_stored_procedures.sql
psql -d stayspot -f sql/05_materialized_views.sql
```

Run `sql/06_window_analytics.sql` as a query once bookings exist (it is a `SELECT`, not DDL).

### Schema

- `guests(id, name, email, wallet_balance CHECK (>= 0), created_at)`
- `wallet_audit_logs(id, guest_id FK, amount_changed, action_type CHECK IN ('DEBIT','CREDIT'), balance_after CHECK (>= 0), timestamp)` — populated **only** by the trigger, never inserted into directly by application code.
- `properties(id, title, base_price CHECK (>0), latitude CHECK (-90..90), longitude CHECK (-180..180), created_at)`
- `bookings(id, guest_id FK, property_id FK, check_in, check_out CHECK (> check_in), total_cost CHECK (>= 0), status CHECK IN ('CONFIRMED','CHECKED_IN','COMPLETED'), created_at)`

### Audit trigger
`fn_log_wallet_audit()` fires `AFTER UPDATE OF wallet_balance ON guests` and inserts one row
into `wallet_audit_logs` per balance change, deriving `action_type` (`DEBIT`/`CREDIT`) from
the direction of the change and recording `balance_after`.

> Note: `wallet_audit_logs` is not additionally locked down with a `REVOKE`/blocking trigger
> against `UPDATE`/`DELETE`. Immutability currently relies on the fact that no script writes
> to it directly. If the viva asks for enforced immutability, this is the one gap to close.

### Partial unique index
`idx_active_stay` on `bookings(guest_id) WHERE status = 'CHECKED_IN'` — a guest can only have
one `CHECKED_IN` booking at a time, exactly as specified in the assignment.

### Materialized view
`property_summary` aggregates, per property: `total_bookings`, `total_nights_booked`
(`SUM(check_out - check_in)`), and `gross_revenue`. A unique index on `property_id` allows
`refresh_property_summary()` to call `REFRESH MATERIALIZED VIEW CONCURRENTLY`.

### Workflow 1 — Atomic booking (`sp_atomic_booking`)
```
CALL sp_atomic_booking(p_guest_id, p_property_id, p_total_cost, p_check_in, p_check_out);
```
1. Validates `check_out > check_in`.
2. Performs a single **conditional** `UPDATE guests SET wallet_balance = wallet_balance - cost
   WHERE id = ... AND wallet_balance >= cost`. If no row matches (insufficient funds),
   `ROW_COUNT` is 0 and the procedure raises an exception.
3. On success, inserts the `bookings` row (status `CONFIRMED`).
4. The wallet `UPDATE` fires `trg_wallet_balance_audit`, so a `wallet_audit_logs` row is
   written as part of the same statement/transaction.

**Deviation from the brief:** rather than an explicit `BEGIN ... EXCEPTION ... ROLLBACK`
block around a `REPEATABLE READ` transaction, atomicity is achieved with a single
conditional `UPDATE` (avoids the race condition without needing manual isolation-level
control), and the whole procedure runs inside the caller's transaction — a failed `CALL`
rolls back automatically. This is called out as an assumption; switch to explicit
`BEGIN`/`EXCEPTION`/`ROLLBACK` with `SET TRANSACTION ISOLATION LEVEL REPEATABLE READ` if the
grader wants the literal pattern from the spec.

### Workflow 2 — Window analytics
`06_window_analytics.sql` computes daily booking revenue per property, a 7-day moving
average via `AVG(...) OVER (PARTITION BY property_id ORDER BY booking_day ROWS BETWEEN 6
PRECEDING AND CURRENT ROW)`, and ranks properties by total revenue with `DENSE_RANK()`.

## 4. MongoDB setup

```bash
mongosh "<connection_string>" mongo/01_collections_and_indexes.js
```

Creates, with `$jsonSchema` validators:
- **PropertyAmenities** — `property_id`, `house_rules[]`, `accessibility_features[]`, free-form `amenities` object. Unique index on `property_id`.
- **PropertyReviews** — `property_id`, `guest_id`, `rating` (1–5), `tags[]`, `comment`, `created_at`. Secondary indexes on `property_id`, `rating`, `tags`.
- **SearchSessions** — `session_id`, GeoJSON `location` (Point), `created_at`. `2dsphere` index on `location`; TTL index on `created_at` with `expireAfterSeconds: 7200` (2 hours).

### Workflow 3 — Trending search hotspots (`02_workflow3_geonear.js`)
`$geoNear` (first pipeline stage, as required) finds `SearchSessions` within 5 km of an
anchor coordinate (default: Bengaluru) created in the last 2 hours, then `$bucket`s them
into 1 km distance bands and counts sessions per band.

### Workflow 4 — Multi-faceted review analytics (`03_workflow4_facet.js`)
`$facet` computes, in one pass over `PropertyReviews`: (1) rating distribution 1–5, (2) top
10 tags via `$unwind` + `$group`, (3) overall average rating and review count. Defaults to
all reviews (`propertyId = null`) so it runs without depending on a hard-coded UUID.

## 5. Data generation

```bash
pip install -r data_generation/requirements.txt
python data_generation/postgres_seeder.py   # update DB_HOST/DB_NAME/DB_USER/DB_PASSWORD at top of file first
python data_generation/mongo_seeder.py      # respects STAYSPOT_MONGO_URI env var, defaults to localhost
```

Actual seeded volumes (as coded, not aspirational):

| Store | Entity | Count |
|---|---|---|
| PostgreSQL | guests | 100000 |
| PostgreSQL | properties | 50000 |
| PostgreSQL | bookings | 1000000 |
| PostgreSQL | wallet_audit_logs | ~100,000 (one per booking, written by the trigger) |
| MongoDB | PropertyAmenities | 1,000 |
| MongoDB | PropertyReviews | 30,000 |
| MongoDB | SearchSessions | 550,000 |

These clear the assignment's minimums (100k+ ledger/audit rows, 50k+ bookings, 500k+ geo
pings). `postgres_seeder.py` uses `execute_values` for bulk inserts; `mongo_seeder.py` uses
batched `bulk_write`/`InsertOne` (batch size 10,000).

## 6. Assumptions

1. `check_in`/`check_out` (`DATE`) were added to `bookings` — not explicit in the base spec,
   but required to compute `total_nights_booked` for the materialized view.
2. All primary keys are UUIDs (`gen_random_uuid()` via `pgcrypto`).
3. `bookings.status` is enforced with a `CHECK` constraint rather than a Postgres `ENUM`,
   for easier migration if new statuses are added later.
4. The partial unique index implements exactly what's specified — one `CHECKED_IN` row per
   guest at a time — not full date-range overlap detection across `CONFIRMED` bookings.
5. `sp_atomic_booking` achieves atomicity via a conditional single-statement `UPDATE`
   instead of an explicit `BEGIN/EXCEPTION/ROLLBACK` block (see Section 3, Workflow 1).
6. `wallet_audit_logs` immutability is enforced only by convention (nothing writes to it
   except the trigger), not by a `REVOKE`/blocking trigger.

## 7. Data source note

Bulk historical `wallet_audit_logs` rows are produced as a side effect of the seeder driving
real `UPDATE`s through the trigger (not inserted directly), so the trigger path is exercised
at full data scale, not just in a one-off demo.

## 8. Performance proof

`performance/postgres_explain_analyzes.txt` and `performance/mongo_execution_stats.json`
currently contain.

**PostgreSQL** — after seeding, run (at minimum) the Workflow 2 window-function query and
the `sp_atomic_booking` path wrapped for inspection, e.g.:
```sql
EXPLAIN (ANALYZE, BUFFERS)
-- paste the Workflow 2 query from sql/06_window_analytics.sql here
```

**MongoDB** — run, and paste the JSON output of:
```js
db.SearchSessions.explain("executionStats").aggregate(pipeline)   // Workflow 3
db.PropertyReviews.explain("executionStats").aggregate(pipeline)  // Workflow 4
```
into `performance/mongo_execution_stats.json`, confirming the `2dsphere` index (`IXSCAN`) is
used for Workflow 3 and the supporting indexes are used for Workflow 4, with no `COLLSCAN`.




## 10 Mongo - WOrflow output
```js // facet
[
  {
    ratingDistribution: [
      {
        _id: 1,
        count: 6040
      },
      {
        _id: 2,
        count: 6042
      },
      {
        _id: 3,
        count: 5931
      },
      {
        _id: 4,
        count: 6051
      },
      {
        _id: 5,
        count: 5936
      }
    ],
    topTags: [
      {
        _id: 'noisy',
        count: 6386
      },
      {
        _id: 'comfortable_beds',
        count: 6370
      },
      {
        _id: 'great_location',
        count: 6350
      },
      {
        _id: 'amazing_view',
        count: 6303
      },
      {
        _id: 'as_described',
        count: 6295
      },
      {
        _id: 'poor_wifi',
        count: 6284
      },
      {
        _id: 'friendly_host',
        count: 6253
      },
      {
        _id: 'clean',
        count: 6238
      },
      {
        _id: 'parking_issues',
        count: 6230
      },
      {
        _id: 'value_for_money',
        count: 6206
      }
    ],
    overallAverage: [
      {
        _id: null,
        avgRating: 2.9933666666666667,
        totalReviews: 30000
      }
    ]
  }
]

// geonear
[
  {
    _id: 4000,
    session_count: 12412,
    avg_distance_m: 4512.524821981002
  },
  {
    _id: 3000,
    session_count: 9634,
    avg_distance_m: 3525.5869114283028
  },
  {
    _id: 2000,
    session_count: 6893,
    avg_distance_m: 2539.0483341525514
  },
  {
    _id: 1000,
    session_count: 4101,
    avg_distance_m: 1557.5506720047103
  },
  {
    _id: 0,
    session_count: 1422,
    avg_distance_m: 666.3892969957219
  }
]
```

## 11. Repo / Commit

- GitHub URL: https://github.com/Jyoti2026201001/Group12_a1
