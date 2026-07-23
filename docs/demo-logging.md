# How to demo Phase IV — Structured Logging

Short walkthrough for demos. Shows end-to-end `X-Request-ID` correlation and
safe JSON logs without dumping secrets.

**Full write-up:** [how-logging-works.md](how-logging-works.md)  
**Contract:** [logging.md](logging.md)

---

## 1. UI demo (best for showing end-to-end)

1. Open `http://localhost:3000` (frontend on your Mac).
2. Open DevTools → **Console** and **Network**.
3. Use either:
   - **Portfolio** tab — login as `alice` / `password`, then View My Portfolio, or
   - **Agent Chat** / **Recommender** — any successful agent call.
4. In Network, click the API request → Response Headers → copy `x-request-id`.
5. In Console, confirm JSON lines like `http_request_started` /
   `http_request_completed` with that same `request_id` (paths and status only —
   no password, no prompt).

Then on EC2, paste that ID into a grep:

```bash
# SSH to EC2 first
RID='<paste-request-id-here>'

cd ~/apira-agent && sudo docker compose logs --since=15m | grep "$RID"
cd ~/apira-mcp && sudo docker compose logs --since=15m | grep "$RID"
cd ~/apira-rag && sudo docker compose logs --since=15m | grep "$RID"
cd ~/apira && sudo docker compose -f docker-compose.backend.yml logs --since=15m | grep "$RID"
```

**Agent Chat / Recommender:** you should see the same ID in agent → mcp
(and rag if research tools ran) → user-service / portfolio-service.

**Portfolio tab only:** matching lines in user-service and portfolio-service
(frontend talks to backends directly).

---

## 2. Prove correlation with curl

From your Mac:

```bash
RID=$(uuidgen | tr '[:upper:]' '[:lower:]')
echo "Using request id: $RID"

curl -sS -D - -o /tmp/apira-chat.json \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: $RID" \
  -X POST "http://<EC2_PUBLIC_IP>:8100/chat" \
  -d '{"message":"Log in as alice with password password and summarize the portfolio holdings briefly."}' \
  | grep -i x-request-id

head -c 200 /tmp/apira-chat.json; echo
```

On EC2, grep that `$RID`. You should see a chain like:

| Service | Events to point at |
|---------|--------------------|
| **apira-agent** | `http.request.started`, `chat.started`, `mcp.tool.started` (`login`, `get_portfolio`) |
| **apira-mcp** | `mcp.tool.started` / `completed`, `upstream.request.completed` |
| **user-service** | `login_succeeded`, `request_completed` |
| **portfolio-service** | `portfolio_fetched`, `request_completed` |

Same `request_id` on every line.

---

## 3. Prove redaction (important)

In those log lines, show:

- `argument_keys":["password","username"]` — **key names only**
- `message_length` / `prompt_length` — **not** the prompt text
- `user_id` / `holdings_count` — **not** the full holdings payload
- No API keys, no `password` values, no reply body in application events

That is the Phase IV safety story: observability without leaking credentials or PII-ish payloads.

---

## 4. Optional — login-only path

```bash
RID=$(uuidgen | tr '[:upper:]' '[:lower:]')

curl -sS -D - \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: $RID" \
  -X POST "http://<EC2_PUBLIC_IP>:8001/login" \
  -d '{"username":"alice","password":"password"}' \
  | grep -i x-request-id
```

On EC2:

```bash
cd ~/apira
sudo docker compose -f docker-compose.backend.yml logs --since=5m | grep "$RID"
```

Expect `login_succeeded` + `request_completed` with your UUID.
