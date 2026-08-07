# Demo walkthrough

Four things from this week, with code links and captured output.

1. Vector-search parameters (similarity, limit, prefer-newer)
2. HNSW vector index in pgvector
3. One `request_id` across Grafana / all services
4. Clear, consistent log messages

**Host:** EC2 `18.188.213.146`  
(user `8001`, portfolio `8002`, agent `8100`, mcp `8000`, rag `8200`, log-service `8300`)

Background docs:

- [vector-search-params.md](../../apira-rag/docs/vector-search-params.md)
- [setup-pgvector-rds.md](../../apira-rag/docs/setup-pgvector-rds.md)
- [how-logging-works.md](how-logging-works.md) · [logging.md](logging.md)
- [grafana-cloud.md](grafana-cloud.md)

---

## 1. Vector-search parameters

Chunks and the query are each turned into an **embedding** (768 numbers that
capture meaning). Search finds chunks whose vectors point in nearly the same
direction as the query.

**Cosine distance** (`<=>` in pgvector) is the angle between those two vectors:
near `0` = almost the same meaning; larger = less related. We show the inverse:

```text
similarity = 1 - distance
```

Closer to `1.0` = tight match; ~`0.5`–`0.7` = related; near `0` = weak.
Compare scores only within one query.

| Knob | Role |
|------|------|
| `query` | Text to embed and search |
| `limit` (default 5) | Matches returned after ranking |
| Candidate pool (`limit × 4`) | Extra neighbors so prefer-newer can drop older docs without emptying results |
| Prefer-newer | Same ticker → keep newest `document_date` |

Flow: embed → cosine nearest neighbors → prefer-newer → return up to `limit`.

### Code

| Piece | Where |
|-------|--------|
| Search + candidate pool | [rag/search.py](../../apira-rag/rag/search.py) (lines 13–24) |
| Cosine → `similarity` | [rag/search.py](../../apira-rag/rag/search.py) (lines 36–52) |
| Prefer-newer | [rag/ranking.py](../../apira-rag/rag/ranking.py) (lines 6–40) |
| Full write-up | [vector-search-params.md](../../apira-rag/docs/vector-search-params.md) |

### Captured output

Query: `AAPL fiscal 2026 second quarter earnings`, `limit=3`

```text
0.7925 AAPL 2026-06-30 aapl-fy2026-q2-earnings.from-pdf.txt
0.7439 AAPL 2026-06-30 aapl-fy2026-q2-earnings.from-pdf.txt
0.7255 AAPL 2026-06-30 aapl-fy2026-q2-earnings.from-pdf.txt
```

```text
pgvector search completed (3 matches from 12 candidates)
```

(`3` returned; `12` = `3 × 4` candidates.)

---

## 2. HNSW vector index

The `embedding vector(768)` column has an HNSW approximate-nearest-neighbor
index:

- Operator class: `vector_cosine_ops` (matches the `<=>` cosine operator)
- `m = 16` — graph connectivity
- `ef_construction = 64` — build quality

No re-embedding required to add it.

### Code

| Piece | Where |
|-------|--------|
| Idempotent `CREATE INDEX` in schema ensure | [rag/schema.py](../../apira-rag/rag/schema.py) (lines 32–40) |
| SQL migration (same DDL) | [sql/migrate_research_chunks_hnsw.sql](../../apira-rag/sql/migrate_research_chunks_hnsw.sql) |
| Unit test for the DDL | [tests/test_schema.py](../../apira-rag/tests/test_schema.py) |
| Docs (opclass, planner note) | [setup-pgvector-rds.md](../../apira-rag/docs/setup-pgvector-rds.md) · [vector-search-params.md](../../apira-rag/docs/vector-search-params.md) |

### Captured output — index exists

```text
INDEX: research_chunks_embedding_hnsw_idx
CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)
  WITH (m='16', ef_construction='64')
size: 1432 kB
chunks: 358
```

### Captured output — planner can use it

At ~358 chunks Postgres often prefers a **sequential scan** because it is
cheaper at this size — that is correct, not a failure. With `enable_seqscan =
off`, the plan uses the index:

```text
Index Scan using research_chunks_embedding_hnsw_idx on research_chunks
  Order By: (embedding <=> ...)
```

As the corpus grows, that plan becomes the default without forcing.

---

## 3. One `request_id` end to end

Every service emits structured JSON logs. The frontend mints one UUID per user
action (`X-Request-ID`) and reuses it for multi-step flows (Recommender login +
`/chat`), so one action is traceable browser → agent → mcp → backends → rag.

Earlier bug: login and chat each minted a fresh UUID. Fixed — one UUID covers
the whole recommender action.

### Code

| Piece | Where |
|-------|--------|
| One UUID for login + chat (Recommender) | [App.jsx](../../apira-frontend/src/App.jsx) (lines 191–226) |
| `apiFetch` accepts / sends `X-Request-ID` | [api.js](../../apira-frontend/src/lib/api.js) (lines 20–34) |
| Agent accepts ID, sets context, echoes header | [server.py](../../apira-agent/server.py) (lines 59–89) |
| Agent forwards ID to both MCP servers | [agent.py](../../apira-agent/agent.py) (lines 73–82) |
| Correlation rules | [logging.md](logging.md) · [how-logging-works.md](how-logging-works.md) |

### In Grafana / the UI

1. Open the frontend, DevTools → Network.
2. Run **Recommender** (login + chat).
3. `/login` and `/chat` response headers both show the **same** `x-request-id`.
4. Grafana Explore (Loki):

```logql
{job=~"docker|apira"} | json | request_id = "<request-id>"
```

### Captured trail (same id across hops)

Shared id from a live check: `d7f74f07-db35-4a4d-852b-705ac89dbde3`

```text
user-service     | login_succeeded          | Login succeeded (user_id=1)
user-service     | request_completed        | HTTP POST /login completed (200)
apira-agent      | http.request.started     | HTTP POST /chat started
apira-agent      | mcp.tool.completed       | MCP tool login completed via apira
apira-agent      | mcp.tool.completed       | MCP tool get_portfolio completed via apira
apira-mcp        | upstream.request.completed | Upstream user-service POST /login completed (200)
apira-mcp        | mcp.portfolio.completed  | get_portfolio completed (5 holdings)
portfolio-service| portfolio_fetched        | Portfolio fetched (5 holdings for user_id=1)
```

(RAG is quiet on that prompt because it did not call research tools.)

---

## 4. Log messages

We audited every service. `event` is the stable filter key; `message` is what
you skim in Grafana and includes the nouns you search for (method+path, tool,
filename, upstream, counts). At default `LOG_LEVEL=INFO` there is roughly one
lifecycle line per hop. High-volume success chatter (per-chunk embeddings,
`/health`, MCP tool middleware) is DEBUG. Third-party noise (httpx, google.genai,
MCP session lines) is quieted to WARNING.

### Code / docs

| Piece | Where |
|-------|--------|
| Message conventions (contract) | [logging.md](logging.md) (§ Message conventions) |
| End-to-end logging story | [how-logging-works.md](how-logging-works.md) |
| Frontend HTTP completion wording | [api.js](../../apira-frontend/src/lib/api.js) (lines 44–48) |
| RAG search completion message | [rag/search.py](../../apira-rag/rag/search.py) (lines 66–78) |

### Example messages

```text
pgvector search completed (3 matches from 12 candidates)
HTTP POST /chat completed (200)
Login succeeded (user_id=1)
Login failed (invalid credentials)
Portfolio fetched (5 holdings for user_id=1)
MCP tool login completed via apira
```
