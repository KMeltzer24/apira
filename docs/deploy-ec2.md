# Deploy Backend to EC2

How **user-service** (8001) and **portfolio-service** (8002) run on EC2 with Docker. The frontend is not deployed — it runs locally only.

```
Postman / curl → EC2 (Docker) → RDS PostgreSQL
```

---

## One-time setup on EC2

Already done for this project:

1. EC2 with Docker and Docker Compose installed
2. App directory: `~/apira/`
3. Security groups: SSH (22), ports 8001 and 8002 from your laptop IP; RDS reachable from EC2
4. Database tables and seed data created in RDS (via pgAdmin)
5. `~/apira/.env` on EC2 with `DATABASE_URL` (not in git):

```bash
DATABASE_URL=postgresql+psycopg2://postgres:<PASSWORD>@<RDS_ENDPOINT>:5432/postgres?sslmode=require
```

URL-encode special characters in the password (e.g. `&` → `%26`).

Deployments use **scp + tarball** (not `git pull`) because the repo is private and EC2 has no GitHub credentials.

---

## Deploy or update

From your Mac, in the project root:

```bash
tar czf /tmp/apira-deploy.tgz user-service portfolio-service docker-compose.backend.yml

scp -i my-ec2-key.pem /tmp/apira-deploy.tgz ec2-user@<EC2_PUBLIC_IP>:/tmp/

ssh -i my-ec2-key.pem ec2-user@<EC2_PUBLIC_IP> \
  "tar xzf /tmp/apira-deploy.tgz -C ~/apira && \
   cd ~/apira && \
   sudo docker compose -f docker-compose.backend.yml up -d --build user-service portfolio-service"
```

- **`--build`** — use after code or dependency changes
- **Restart only** — drop `--build`: `up -d user-service portfolio-service`
- The tarball does not include `.env`, so the RDS password on EC2 is kept

---

## Verify

**From your Mac:**

```bash
curl -X POST http://<EC2_PUBLIC_IP>:8001/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"password"}'

curl "http://<EC2_PUBLIC_IP>:8002/portfolio?user_id=1"
```

Both should return HTTP 200 and JSON.

**On EC2:**

```bash
cd ~/apira
sudo docker compose -f docker-compose.backend.yml ps
sudo docker compose -f docker-compose.backend.yml logs --tail=30
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Timeout from Mac | EC2 stopped, or security group / your public IP changed |
| Works on EC2, not from Mac | Update inbound rules for ports 8001 and 8002 |
| Container crashes | Check logs; verify `~/apira/.env` and RDS |

**Restart:** `sudo docker compose -f docker-compose.backend.yml up -d user-service portfolio-service`  
**Stop:** `sudo docker compose -f docker-compose.backend.yml down`

Replace `<EC2_PUBLIC_IP>` and `<RDS_ENDPOINT>` with values from the AWS console.
