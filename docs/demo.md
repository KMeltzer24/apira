# Demo & verification guide

How to **show** the four deliverables working end to end. Each section has a
"what to say" summary and copy-paste commands that produce visible proof.

Deliverables covered:

1. Explain the vector-search parameters (e.g. similarity)
2. Implement + prove the vector index (HNSW) in pgvector
3. Grafana logs are complete and share one `request_id`
4. All log messages make sense

**Live host:** EC2 `18.188.213.146` (ports: user `8001`, portfolio `8002`,
agent `8100`, mcp `8000`, rag `8200`, log-service `8300`).
SSH: `ssh -i ~/development/apira/my-ec2-key.pem ec2-user@18.188.213.146`.

Reference docs:

- Vector params: [apira-rag/docs/vector-search-params.md](https://github.com/KMeltzer24/apira-rag/blob/main/docs/vector-search-params.md)
- pgvector/RDS + HNSW: [apira-rag/docs/setup-pgvector-rds.md](https://github.com/KMeltzer24/apira-rag/blob/main/docs/setup-pgvector-rds.md)
- Logging story: [how-logging-works.md](how-logging-works.md) · contract: [logging.md](logging.md)
- Grafana: [grafana-cloud.md](grafana-cloud.md)

---

## 1. Vector-search parameters (similarity)

**Say:** search embeds the query with Gemini, orders chunks by **cosine
distance** (`embedding <=> query_vector`), and returns
`similarity = 1 - distance`. `limit` caps returned matches; a larger candidate
pool (`limit * 4`) feeds prefer-newer so newer same-ticker docs win ties.

Full reference: [vector-search-params.md](https://github.com/KMeltzer24/apira-rag/blob/main/docs/vector-search-params.md).

**Show — run a live search and read the scores:**

```bash
ssh -i ~/development/apira/my-ec2-key.pem ec2-user@18.188.213.146
sudo docker exec apira-rag-rag-server-1 python -c "
import json
from rag.search import search_vector_db
res = search_vector_db('AAPL fiscal 2026 second quarter earnings', 3)
for m in res['matches']:
    print(round(m['similarity'], 4), m['ticker'], m['document_date'], m['filename'])
"
```

Expected shape (real output):

```text
0.7925 AAPL 2026-06-30 aapl-fy2026-q2-earnings.from-pdf.txt
0.7439 AAPL 2026-06-30 aapl-fy2026-q2-earnings.from-pdf.txt
0.7255 AAPL 2026-06-30 aapl-fy2026-q2-earnings.from-pdf.txt
```

**Point out:**

- Scores descend (`0.79 > 0.74 > 0.73`) — closer to `1.0` = tighter match.
- The `rag.db_search.completed` log line shows `match_count` and
  `candidate_count` (e.g. `3 matches from 12 candidates`).
- Prefer-newer: query a ticker that has both an old and a new doc and confirm
  the newer `document_date` ranks first.

---

## 2. Vector index (HNSW)

**Say:** the `embedding vector(768)` column has an HNSW ANN index using
`vector_cosine_ops` (matches the `<=>` operator), `m = 16`,
`ef_construction = 64`. It is applied idempotently by `rag/schema.py` and lives
as `sql/migrate_research_chunks_hnsw.sql`. No re-embedding needed.

**Show — the index exists:**

```bash
sudo docker exec apira-rag-rag-server-1 python -c "
from rag.db import get_connection
with get_connection() as c, c.cursor() as cur:
    cur.execute(\"SELECT indexname, indexdef FROM pg_indexes WHERE indexname='research_chunks_embedding_hnsw_idx'\")
    print(cur.fetchall())
    cur.execute(\"SELECT pg_size_pretty(pg_relation_size('research_chunks_embedding_hnsw_idx'))\")
    print('size', cur.fetchone())
    cur.execute('SELECT count(*) FROM research_chunks')
    print('chunks', cur.fetchone())
"
```

Expected: one row, `USING hnsw (embedding vector_cosine_ops) WITH (m='16', ef_construction='64')`, size ~1.4 MB, 358 chunks.

**Show — the planner can use it:**

```bash
sudo docker exec apira-rag-rag-server-1 python -c "
from rag.db import get_connection
with get_connection() as c, c.cursor() as cur:
    cur.execute('SET enable_seqscan = off')
    cur.execute('EXPLAIN SELECT id FROM research_chunks ORDER BY embedding <=> (SELECT embedding FROM research_chunks LIMIT 1) LIMIT 5')
    print('\n'.join(r[0] for r in cur.fetchall()))
"
```

Expected: `Index Scan using research_chunks_embedding_hnsw_idx`.

> **Important caveat to state up front:** with only ~358 chunks the planner
> *normally* picks a **sequential scan** because it is cheaper at this size —
> that is correct behaviour, not a bug. `SET enable_seqscan = off` proves the
> index is valid and usable; it becomes the default plan as the corpus grows.

---

## 3. Grafana logs complete + one `request_id`

**Say:** every service emits JSON logs with a shared `request_id`. The frontend
mints one UUID per user action (`X-Request-ID`) and reuses it across multi-step
flows (login + `/chat`), so one action is traceable browser → agent → mcp →
backends/rag.

**Show (browser path):**

1. Open the frontend, DevTools → Network, run **Recommender** (login + chat).
2. On the `/chat` request, copy the response header `x-request-id`.
3. In Grafana Explore (Loki), filter by it:

```logql
{job=~"docker|apira"} | json | request_id = "<request-id>"
```

You should see lines from `apira-frontend`, `apira-agent`, `apira-mcp`,
`user-service`, `portfolio-service`, and (if research ran) `apira-rag` — all
with the **same** `request_id`.

**Show (host path, no Grafana):**

```bash
cd ~/apira && sudo docker compose -f docker-compose.backend.yml logs --since=10m | grep '<request-id>'
```

**Point out:** the frontend now generates one UUID for the whole recommender
action instead of a fresh one per call, so the IDs line up across hops (this was
the earlier mismatch we fixed).

---

## 4. Log messages make sense

**Say:** we did a service-by-service audit. `event` is the stable filter key;
`message` is human-readable and carries the nouns people search for
(method+path, tool, filename, upstream, counts). One INFO lifecycle line per hop
at default `LOG_LEVEL`; noisy chatter demoted to DEBUG.

Conventions live in [logging.md](logging.md#message-conventions).

**Show — tail one service and read the messages:**

```bash
cd ~/apira-rag && sudo docker compose logs --tail=20 rag-server
```

Look for clear lines like:

- `pgvector search completed (3 matches from 12 candidates)`
- `HTTP POST /chat completed (200)` (agent)
- `Login succeeded (user_id=1)` / `Login failed (invalid credentials)`
- `Portfolio fetched (5 holdings for user_id=1)`
- `MCP tool login completed via apira`

**Point out what got quieter:** per-chunk embedding logs, `/health`, and MCP
tool middleware lifecycle are now DEBUG; third-party library chatter (httpx,
google.genai, MCP session/protocol lines) is silenced to WARNING.

---

## One-shot smoke check

Confirm every container is up and serving:

```bash
ssh -i ~/development/apira/my-ec2-key.pem ec2-user@18.188.213.146 \
  'sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
```

Expect `alloy`, `log-service`, `user-service`, `portfolio-service`,
`rag-server`, `mcp-server`, `agent` all `Up`.

---

## Notes / known limits

- **Memory:** the instance is 916 MB with no swap. Avoid on-box
  `docker compose up --build` (it OOM-thrashes). Ship images or `docker cp`
  changed files, or add a 2 GB swap file first.
- **HNSW at this size** may not change latency yet; it is the correct durable
  choice and costs ~1.4 MB on RDS.
- No similarity floor today — weak matches can still return if nothing better
  is in the candidate pool.
