# ORATOR 🗣️ : THE ONLY WAY TO LISTEN TO PDFs AND EPUBs
![](/Users/kayparmar/Desktop/code/Projects/ORATOR/System_Design.png)
## <ins>Outline<ins>
- [ORATOR 🗣️ : THE ONLY WAY TO LISTEN TO PDFs AND EPUBs](#orator-️--the-only-way-to-listen-to-pdfs-and-epubs)
  - [Outline](#outline)
  - [Build \& Setup Guide](#build--setup-guide)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Environment variables](#2-environment-variables)
  - [3. One‑command container build](#3-onecommand-container-build)
    - [Verify](#verify)
  - [4. Local development without Docker](#4-local-development-without-docker)
    - [4.1 Backend](#41-backend)
    - [4.2 Front‑end (Vite + React + TS)](#42-frontend-vitereactts)
    - [4.3 Watching Celery](#43-watching-celery)
  - [5. Useful Make targets](#5-useful-make-targets)
  - [6. Running tests](#6-running-tests)
  - [7. CI](#7-ci)
  - [8. Cleaning up](#8-cleaning-up)
- [Development Style](#development-style)
    - [Sponsor me \<3](#sponsor-me-3)

## Build & Setup Guide

**TL;DR**

```bash
git clone https://github.com/kayo09/orator.git
cd orator
docker compose up --build -d      # full stack (API, Celery, Redis, ClamAV, Flower)
# browse http://localhost:8000/docs  – FastAPI swagger
# browse http://localhost:5555       – Celery Flower dashboard
```

## 1. Prerequisites

| Component             | Recommended version                    |
| --------------------- | -------------------------------------- |
| Docker Engine         | ≥ 24.x                                 |
| Docker Compose plugin | ≥ v2.x                                 |
| Node.js               | ≥ 20.x (for front‑end dev)             |
| Python                | 3.11 (optional dev outside containers) |

## 2. Environment variables

The stack works out‑of‑the‑box thanks to sane defaults hard‑coded in `celery_config.py`, but you can overwrite via **Backend/.env**:

```env
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CLAMD_HOST=clamav
CLAMD_PORT=3310
ENABLE_ANTIVIRUS=true
```

(See `docker-compose.yml` for the variables passed to each service). ([raw.githubusercontent.com](https://raw.githubusercontent.com/kayo09/orator/main/docker-compose.yml))

## 3. One‑command container build

1. Clone the repo.
2. From the project root:

```bash
docker compose up --build -d
```

Compose spins up five services — `redis`, `clamav`, `orator-api` (FastAPI), `orator-celery` (Celery worker), and `orator-flower` (task dashboard). ([raw.githubusercontent.com](https://raw.githubusercontent.com/kayo09/orator/main/docker-compose.yml))

> Tip: run `make up` instead; the Makefile wraps common compose recipes. ([raw.githubusercontent.com](https://raw.githubusercontent.com/kayo09/orator/main/Makefile))

### Verify

* Flower:  [http://localhost:5555](http://localhost:5555) (needs all containers healthy)

Stop everything:

```bash
docker compose down -v
```

(Or `make down`.)

## 4. Local development without Docker

### 4.1 Backend

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r Backend/requirements.txt              # backend deps ([raw.githubusercontent.com](https://raw.githubusercontent.com/kayo09/orator/main/Backend/requirements.txt))
brew services start redis                            # or docker run ...
docker run -d --name clamav -p 3310:3310 clamav/clamav-debian:latest
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=$CELERY_BROKER_URL
uvicorn Backend.main:app --reload --port 8000 &
celery -A Backend.celery_config worker --pool=threads --concurrency=4 --loglevel=info &
```

### 4.2 Front‑end (Vite + React + TS)

```bash
cd Frontend
npm install
npm run dev          # served on http://localhost:5173 by default
```

(See `package.json` for available scripts.) ([raw.githubusercontent.com](https://raw.githubusercontent.com/kayo09/orator/main/Frontend/package.json))

### 4.3 Watching Celery

```bash
docker run --rm -p 5555:5555 --network host \
  -e CELERY_BROKER_URL=$CELERY_BROKER_URL \
  mher/flower
```

## 5. Useful Make targets

| Target           | What it does                                      |
| ---------------- | ------------------------------------------------- |
| `make up`        | `docker compose up --build`                       |
| `make shell-api` | Drop into FastAPI container                       |
| `make logs`      | Tail all service logs                             |
| `make test`      | Run backend Pytest suite inside the API container |

(More in `Makefile`.) ([raw.githubusercontent.com](https://raw.githubusercontent.com/kayo09/orator/main/Makefile))

## 6. Running tests

Tests live in `test/`. Inside the API container or local venv:

```bash
pytest -q
```

## 7. CI

GitHub Actions (`.github/workflows/ci.yaml`) runs linting and tests on every push using the same Docker images—so your build should pass locally before opening PRs.

## 8. Cleaning up

```bash
docker compose down --volumes --remove-orphans
docker system prune -af            # optional, frees disk
```

---
# Development Style
> https://en.wikipedia.org/wiki/Twelve-Factor_App_methodology
> <table class="wikitable" style="text-align:left">
<caption>The Twelve Factors<sup id="cite_ref-Red1_1-2" class="reference"><a href="#cite_note-Red1-1"><span class="cite-bracket">[</span>1<span class="cite-bracket">]</span></a></sup><sup id="cite_ref-The12_2-0" class="reference"><a href="#cite_note-The12-2"><span class="cite-bracket">[</span>2<span class="cite-bracket">]</span></a></sup>
</caption>
<tbody><tr>
<th>#</th>
<th>Factor</th>
<th>Description
</th></tr>
<tr>
<td>I</td>
<td>Codebase</td>
<td>There should be exactly one codebase for a deployed service with the codebase being used for many deployments.
</td></tr>
<tr>
<td>II</td>
<td>Dependencies</td>
<td>All dependencies should be declared, with no implicit reliance on system tools or libraries.
</td></tr>
<tr>
<td>III</td>
<td>Config</td>
<td>Configuration that varies between deployments should be stored in the environment.
</td></tr>
<tr>
<td>IV</td>
<td>Backing services</td>
<td>All backing services are treated as attached resources and attached and detached by the execution environment.
</td></tr>
<tr>
<td>V</td>
<td>Build, release, run</td>
<td>The delivery pipeline should strictly consist of build, release, run.
</td></tr>
<tr>
<td>VI</td>
<td>Processes</td>
<td>Applications should be deployed as one or more stateless processes with persisted data stored on a backing service.
</td></tr>
<tr>
<td>VII</td>
<td><a href="/wiki/Port_(computer_networking)" title="Port (computer networking)">Port</a> binding</td>
<td>Self-contained services should make themselves available to other services by specified ports.
</td></tr>
<tr>
<td>VIII</td>
<td><a href="/wiki/Concurrent_computing" title="Concurrent computing">Concurrency</a></td>
<td>Concurrency is advocated by scaling individual processes.
</td></tr>
<tr>
<td>IX</td>
<td>Disposability</td>
<td>Fast startup and shutdown are advocated for a more robust and resilient system.
</td></tr>
<tr>
<td>X</td>
<td>Dev/Prod parity</td>
<td>All environments should be as similar as possible.
</td></tr>
<tr>
<td>XI</td>
<td>Logs</td>
<td>Applications should produce logs as event streams and leave the execution environment to aggregate.
</td></tr>
<tr>
<td>XII</td>
<td>Admin Processes</td>
<td>Any needed admin tasks should be kept in source control and packaged with the application.
</td></tr></tbody></table>

**upgrade guide:**
diagnose → optimise → polish the UI → tighten the backend contract
### Sponsor me <3
https://github.com/sponsors/kayo09/
