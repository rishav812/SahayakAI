# Deployment Guide — SahayakAI on AWS (EC2 + RDS)

This is a step-by-step guide for deploying this FastAPI app to a single AWS
EC2 instance, backed by an RDS PostgreSQL database, with a GitHub Actions
CI/CD pipeline on top.

**Approach:** no Docker. The app runs directly in a Python virtualenv,
managed by `systemd`, with Nginx as a reverse proxy in front of it. See the
"Why no Docker" note at the bottom for the reasoning — short version: this is
a single instance running a single service, so the extra abstraction layer
isn't buying us much, and skipping it means everything you learn in the
pipeline is CI/CD, not CI/CD-through-Docker.

Work through the phases in order. Each phase depends on the state left by
the previous one.

---

## Phase 0 — Make the app production-ready (do this first, no AWS yet)

A few things in the current code will bite you specifically because you're
about to run this outside your dev machine. Fix these before touching AWS:

- [ ] **README run command is stale.** `app/main.py` does
      `from app.routes import router`, which only resolves if you run uvicorn
      as a package from the **repo root**:
      `uvicorn app.main:app --host 0.0.0.0 --port 8000`
      (not `uvicorn main:app` as the README currently says). This is the
      exact command you'll put in the systemd unit file in Phase 4 — get it
      right here first by testing locally from the repo root.

- [ ] **`app/graph.py` makes a network call at import time.**
      `admissions_agent.get_graph().draw_mermaid_png()` calls out to
      `mermaid.ink` every time the module is imported — i.e. every app
      startup. On a fresh EC2 box this means your app **won't start** until
      that external call succeeds, which is a fragile thing to depend on in
      production (security group egress, mermaid.ink being down/rate-limited,
      slower cold starts). Worth wrapping in a `try/except` (or gating behind
      an env var like `DRAW_GRAPH=false` in prod) before you deploy. Flag for
      later — happy to help you fix this when you get here.

- [ ] **`CHROMA_DIR = "chroma_db"` is a relative path.** It resolves
      relative to whatever directory the process is started from. Since
      there's no Docker, this isn't a "volume" problem — it'll just persist
      as a normal folder on disk — but the systemd `WorkingDirectory=` **must**
      be the repo root or this silently creates a second, empty `chroma_db`
      somewhere else and your `/ingest` data goes "missing."

- [ ] **`.env` currently holds `OPENAI_API_KEY` and `DATABASE_URL`.** Locally
      this is fine; in prod, this file will live only on the EC2 box (never
      committed, never passed through GitHub Actions logs). More in Phase 4.

---

## Phase 1 — AWS account & CLI setup

- [ ] Confirm you can log into the AWS Console.
- [ ] **Set a billing alarm first** (Billing → Budgets → create a budget,
      e.g. $10) — free tier covers this setup, but it's easy to forget a
      resource running and get a surprise bill.
- [ ] Create an IAM user for yourself (not root) with `AdministratorAccess`
      for now (you can tighten this later) — Console → IAM → Users → Create.
- [ ] Generate an access key for that user (IAM → Users → your user →
      Security credentials → Create access key → "Command Line Interface").
- [ ] Install the AWS CLI locally and run `aws configure`, pasting in the
      access key, secret key, and your preferred region (e.g. `ap-south-1`
      for Mumbai, given your users are in India).
- [ ] Verify: `aws sts get-caller-identity` should print your account ID.

---

## Phase 2 — Provision RDS (PostgreSQL)

The database has to exist before the app can start, since `app/graph.py`
connects to it at import time.

- [ ] Console → RDS → Create database.
- [ ] Engine: **PostgreSQL**.
- [ ] Template: **Free tier**.
- [ ] DB instance identifier: e.g. `sahayakai-db`.
- [ ] Master username/password — save these somewhere safe (password
      manager, not chat).
- [ ] Instance class: `db.t3.micro` / `db.t4g.micro` (whatever free tier
      offers in your region).
- [ ] Storage: default (20GB gp2/gp3) is fine.
- [ ] **Public access: No.** The database should only be reachable from
      inside the VPC, never the open internet.
- [ ] VPC security group: create a new one, name it something like
      `sahayakai-rds-sg`. Leave the inbound rule empty for now — you'll add a
      rule in Phase 3 once the EC2 security group exists, so only EC2 can
      reach port 5432.
- [ ] Create the database. Wait for status "Available" (~5-10 min).
- [ ] Copy the endpoint hostname (RDS → Databases → your db → Connectivity
      & security → Endpoint). Your connection string will be:
      ```
      postgresql://<username>:<password>@<endpoint>:5432/postgres
      ```
      (matches the `DATABASE_URL` shape `app/config.py` expects.)

---

## Phase 3 — Provision EC2

- [ ] Console → EC2 → Launch instance.
- [ ] Name: `sahayakai-app`.
- [ ] AMI: **Ubuntu Server 22.04 LTS**.
- [ ] Instance type: `t3.micro` (or `t2.micro` — whichever is free-tier
      eligible in your account).
- [ ] Key pair: create a new one, download the `.pem` file. This is what
      you'll SSH in with — keep it safe, you can't re-download it.
- [ ] Network settings → create a new security group, `sahayakai-ec2-sg`,
      with inbound rules:
      - SSH (22) — source: **My IP** (not 0.0.0.0/0 — no need to expose SSH
        to the whole internet)
      - HTTP (80) — source: Anywhere (0.0.0.0/0) — this is what Nginx will
        listen on
- [ ] Storage: default 8GB is enough for this app.
- [ ] Launch the instance.
- [ ] Once it's running, go back to the **RDS security group** from Phase 2
      and add an inbound rule: PostgreSQL (5432), source = the
      `sahayakai-ec2-sg` security group (not an IP — the security group
      itself). This is what lets only your EC2 box reach the database.
- [ ] SSH in to confirm access:
      ```
      ssh -i /path/to/your-key.pem ubuntu@<EC2_PUBLIC_IP>
      ```

---

## Phase 4 — Manual deploy (do this by hand before automating anything)

This is the most important phase to actually type out yourself — it's the
reference you'll fall back on if the pipeline ever breaks, and you can't
automate a process you haven't done manually at least once.

On the EC2 box:

- [ ] Install system dependencies:
      ```
      sudo apt update && sudo apt upgrade -y
      sudo apt install -y python3.10 python3.10-venv python3-pip git nginx libpq-dev
      ```
- [ ] Clone the repo:
      ```
      git clone https://github.com/rishav812/SahayakAI.git app
      cd app
      ```
- [ ] Create the venv and install deps:
      ```
      python3.10 -m venv .venv
      source .venv/bin/activate
      pip install -r requirements.txt
      ```
- [ ] Create the production `.env` file (this file stays only on this box,
      never in git):
      ```
      nano .env
      ```
      ```
      OPENAI_API_KEY=sk-...
      DATABASE_URL=postgresql://<username>:<password>@<rds-endpoint>:5432/postgres
      ```
- [ ] Test it runs manually first:
      ```
      uvicorn app.main:app --host 0.0.0.0 --port 8000
      ```
      From your own machine: `curl http://<EC2_PUBLIC_IP>:8000/` should
      return `{"status": "ok"}`. Ctrl+C to stop once confirmed.

- [ ] Create a systemd service so the app survives reboots and crashes.
      `sudo nano /etc/systemd/system/sahayakai.service`:
      ```ini
      [Unit]
      Description=SahayakAI FastAPI app
      After=network.target

      [Service]
      User=ubuntu
      WorkingDirectory=/home/ubuntu/app
      EnvironmentFile=/home/ubuntu/app/.env
      ExecStart=/home/ubuntu/app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
      Restart=on-failure

      [Install]
      WantedBy=multi-user.target
      ```
      ```
      sudo systemctl daemon-reload
      sudo systemctl enable --now sahayakai
      sudo systemctl status sahayakai
      ```

- [ ] Put Nginx in front of it as a reverse proxy (so port 80 → 8000, and
      you have room to add HTTPS later without touching the app).
      `sudo nano /etc/nginx/sites-available/sahayakai`:
      ```nginx
      server {
          listen 80;
          server_name _;

          location / {
              proxy_pass http://127.0.0.1:8000;
              proxy_set_header Host $host;
              proxy_set_header X-Real-IP $remote_addr;
          }
      }
      ```
      ```
      sudo ln -s /etc/nginx/sites-available/sahayakai /etc/nginx/sites-enabled/
      sudo rm /etc/nginx/sites-enabled/default
      sudo nginx -t && sudo systemctl restart nginx
      ```

- [ ] Confirm from your own machine: `curl http://<EC2_PUBLIC_IP>/` returns
      `{"status": "ok"}`, and `POST /message` works end to end.

At this point you have a fully working manual deployment. Everything after
this is automating exactly what you just did by hand.

---

## Phase 5 — CI (GitHub Actions): test on every push

Goal: nothing broken ever reaches `main`. Runs `pytest` on every push/PR —
no AWS access needed for this phase.

- [ ] `.github/workflows/ci.yml` — checkout, set up Python 3.10, install
      `requirements.txt`, run `pytest`.
- [ ] Push a branch, open a PR, confirm the check runs and passes.

*(We'll write this workflow together when you get here — it's a good next
step once Phase 4 is solid.)*

---

## Phase 6 — CD (GitHub Actions): deploy on merge to main

Goal: automate exactly the manual steps from Phase 4 — pull latest code,
reinstall deps, restart the service — triggered after CI passes on `main`.

You'll need these as GitHub repo secrets (Settings → Secrets and variables
→ Actions):
- `EC2_HOST` — the public IP
- `EC2_USER` — `ubuntu`
- `EC2_SSH_KEY` — contents of the `.pem` file from Phase 3

The workflow SSHs in and runs roughly:
```bash
cd /home/ubuntu/app
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart sahayakai
```

*(We'll write this workflow together too, once Phase 5 is working — deploy
automation should come after test automation, not before.)*

---

## Phase 7 — Hardening (once the basics work end-to-end)

Not needed for a first deploy, but the next things worth learning once
Phases 0-6 are solid:
- Move `OPENAI_API_KEY` / `DATABASE_URL` out of a plain `.env` file and into
  AWS Systems Manager Parameter Store (free) or Secrets Manager.
- Attach an IAM role to the EC2 instance instead of using long-lived AWS
  keys, if you ever need the box itself to call AWS APIs.
- Add HTTPS via Certbot/Let's Encrypt once you have a domain pointed at the
  instance.
- CloudWatch alarms for CPU/disk, and RDS automated backups (on by default,
  worth confirming retention).
- An Elastic IP, so the public IP doesn't change if the instance is
  stopped/started.

---

## Why no Docker (for now)

Decision recap, in case future-you wonders: this is one service on one
instance, no orchestrator, no multi-instance rollout planned. Docker's real
advantages — identical native-dependency builds across environments, and
atomic rollback via image tags — mostly apply once you're deploying to more
than one place or need instant rollback. Here, `pip install` runs directly
on the target Ubuntu box, so it resolves Linux wheels natively regardless.
If a second service, an orchestrator, or a real rollback requirement shows
up later, that's the point to revisit this — not before.
