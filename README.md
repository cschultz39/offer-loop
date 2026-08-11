# OfferLoop - Job Search Agent

An automated pipeline that collects new-grad Software Engineering / Forward Deployed Engineer postings, scores them against personal preferences with Claude, stores results in Supabase (Postgres), and serves them through a Next.js dashboard (FastAPI backend) — with a daily Slack digest.

Built as a personal tool for a Summer/Fall 2027 new-grad job search, and as a hands-on project in agentic tooling with the Claude API and full-stack development.

## Architecture overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Data sources   │ --> │  Collector       │ --> │  Supabase       │
│  (GitHub repos) │     │  (collect_github │     │  (Postgres)     │
│                 │     │  .py)            │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                 │                        │
                                 v                        v
                        ┌──────────────────┐     ┌─────────────────┐
                        │  Claude API      │     │  Slack digest   │
                        │  classification  │     │  (slack_report  │
                        │  (relevance)     │     │  .py)           │
                        └──────────────────┘     └─────────────────┘

                        ┌──────────────────────────────────────────┐
                        │  FastAPI backend                         │
                        │  /jobs, /jobs/status, /metrics,          │
                        │  /history, /chat                         │
                        └──────────────────────────────────────────┘
                                             │
                                             v
                        ┌──────────────────────────────────────────┐
                        │  Next.js + Tailwind dashboard            │
                        │  Metrics tiles, status-history chart,    │
                        │  unapplied jobs list, chat widget        │
                        │  — pixelated strawberry-matcha UI        │
                        └──────────────────────────────────────────┘

         Collection pipeline runs daily via GitHub Actions
         (.github/workflows/daily.yml)
```

**Note:** originally a Streamlit dashboard reading from Google Sheets. Migrated to Next.js + Tailwind + FastAPI (Streamlit's CSS/layout limits and slow full-script reruns) and to Supabase/Postgres (`db_tools.py`, replacing `sheet_tools.py`). `dashboard.py` is kept for reference only; `agent.py`'s tool-use logic now powers the `/chat` endpoint.

## What it does

1. **Collects** active new-grad SWE postings from `speedyapply/2027-SWE-College-Jobs` and `vanshb03/New-Grad-2027`
2. **Filters** by title keywords and active/visible status
3. **Deduplicates** via `id` lookup and canonicalized-link comparison, so the same posting reached through different sources/query strings doesn't create duplicate rows
4. **Fetches** full posting text (`fetch_job_text.py`) — direct ATS JSON API first (`ats_apis.py`, Greenhouse/Workday), Playwright for other JS-rendered boards (Ashby, remaining Workday, Meta Careers, Workable, iCIMS, Dayforce), `requests`/BeautifulSoup otherwise. Dead or closed postings are skipped before classification.
5. **Classifies** each posting with Claude against personal preferences: location tier, grad-year match (2027 preferred, 2026 excluded), Python/AI-agent/LLM-usage signal, and hard-excludes for defense/government contractors and companies linked to ICE/surveillance work (blocklist checked before the Claude call, so those postings skip both the fetch and the API call)
6. **Stores** results in Supabase — a `job_postings` table (company, title, location, link, source, dates, status, relevance score/reason) and a `status_history` table logging every status transition
7. **Reports** new postings to Slack once a day, sorted by relevance score
8. **Runs automatically** every day via a GitHub Actions scheduled workflow
9. **Serves a dashboard** — status tiles, a weekly status-history chart, the top 10 unapplied jobs, and a chat widget for natural-language search and status updates

## File structure

```
job-search-agent/
├── collect_github.py          # Main collector: fetch, filter, dedup, fetch text, classify, write to db
├── fetch_job_text.py          # JobTextFetcher — routes text extraction between ATS APIs, Playwright, requests/BeautifulSoup
├── ats_apis.py                 # Direct JSON API access for Greenhouse and Workday
├── db_tools.py                 # Shared Supabase read/write logic (used by API + collector)
├── slack_report.py             # Formats and sends today's new postings to Slack
├── reclassify.py               # One-off batch re-classification of existing rows
├── check_extraction.py         # Diagnostic: buckets extraction quality (good/thin/closed/blocked/dead) across saved postings
├── agent.py                    # Claude tool-use agent: search_jobs / mark_status tools, backs the /chat endpoint
├── dashboard.py                # Legacy Streamlit chat UI (superseded — see note above)
├── sources/
│   ├── __init__.py
│   ├── simplifyjobs.py         # SimplifyJobs source (disabled — 2026 postings only)
│   ├── speedyapply.py          # speedyapply 2027-SWE-College-Jobs source
│   └── newgrad2027.py          # vanshb03/New-Grad-2027 source
├── api/                         # FastAPI backend
│   ├── __init__.py              # Makes api/ importable — required for Railway's `uvicorn api.main:app` start command
│   └── main.py                  # /jobs, /jobs/status, /metrics, /history, /chat endpoints
├── frontend/                    # Next.js + Tailwind dashboard
│   ├── app/
│   │   ├── layout.tsx            # Root layout — Pixelify Sans + Press Start 2P fonts
│   │   ├── page.tsx              # Main dashboard page
│   │   ├── globals.css           # Strawberry-matcha color tokens, pixel-art tile/card styles
│   │   └── api/[...path]/route.ts  # Catch-all proxy: forwards requests to FastAPI, attaching API_SECRET server-side
│   ├── components/
│   │   ├── MetricsTiles.tsx      # Status count tiles, colors from lib/statusColors.ts
│   │   ├── StatusChart.tsx       # Weekly status-history chart (Recharts)
│   │   ├── UnappliedJobs.tsx     # Scrollable unapplied jobs list
│   │   ├── JobCard.tsx           # Shared job card: apply link, Mark Applied, Not Interested
│   │   └── ChatWidget.tsx        # Floating chat widget — talks to /chat, renders JobCards
│   └── lib/
│       ├── api.ts                # Fetch wrappers for the FastAPI backend
│       └── statusColors.ts       # Single source of truth for status -> color/label mapping
├── .github/workflows/
│   └── daily.yml                 # Scheduled automation (collector + Slack report)
├── requirements.txt              # Single consolidated dependency list (Railway builds from repo root)
├── .env                          # Local secrets (not committed)
├── service_account.json          # Google service account credentials (not committed)
└── .gitignore
```

## Data sources

| Source | Status | Notes |
|---|---|---|
| `speedyapply/2027-SWE-College-Jobs` | Active | Markdown table, parsed via `sources/speedyapply.py` |
| `vanshb03/New-Grad-2027` | Active | Markdown table, parsed via `sources/newgrad2027.py`; filters closed (🔒) postings and anything before 2026-07-24 |
| `SimplifyJobs/New-Grad-Positions` | Disabled | 2026 postings only — re-enable once 2027 roles are added |

## Classification logic

Each posting is scored by Claude against personal preferences:
- **Location**, ranked: Chicago > Chicagoland > Big Midwest cities > Portland/Washington > anywhere in the USA
- **No preference** on company type or size
- **Hard dealbreakers** (score 1, not relevant): defense/government/clearance-required roles; companies linked to ICE or mass surveillance (blocklist checked first, Claude prompt as fallback)

Dealbreaker postings are still written to the database (visible, scored low) so classification accuracy can be spot-checked.

## Environment variables / secrets

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API access (classification + agent) |
| `GH_TOKEN_PAT` | GitHub API token (higher rate limits) |
| `SLACK_WEBHOOK_URL` | Incoming webhook for the daily Slack digest |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key (server-side only) |
| `FASTAPI_URL` | Base URL the Next.js proxy (server-side only) |
| `API_SECRET` | Shared secret required on every FastAPI request; attached server-side by the Next.js proxy. Same value set on both Vercel and Railway |
| `FRONTEND_URL` | Live Vercel domain, used for CORS in `api/main.py` |

Locally, the Python-side variables live in `.env`. In GitHub Actions, they're stored as repository secrets. The frontend's `FASTAPI_URL`/`API_SECRET` live in `frontend/.env.local` (gitignored) and must be mirrored in Vercel's project settings.

**Note:** the browser never talks to Railway directly — `lib/api.ts` calls same-origin `/api/...` routes, which `app/api/[...path]/route.ts` proxies to FastAPI, attaching `x-api-key: API_SECRET` server-side.

## Running locally

```powershell
# Python side (collector, Slack report, FastAPI backend)
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
 
python collect_github.py      # fetch, filter, classify, save new postings
python slack_report.py        # send today's new postings to Slack
uvicorn api.main:app --reload # launch the FastAPI backend
 
# Frontend
cd frontend
npm install
npm run dev                   # launch the Next.js dashboard
```

## Deployment

- **Frontend**: Next.js on Vercel. Root Directory `frontend`; `FASTAPI_URL` (server-only) points at Railway, `API_SECRET` is attached to every proxied request. The browser only ever calls same-origin `/api/...` routes.
- **Backend**: FastAPI on Railway. Root Directory is the **repo root** (not `api/`), since `api/main.py` imports `db_tools.py` from the parent directory and `requirements.txt` lives at repo root. Every route except `/health` requires an `x-api-key: API_SECRET` header (`verify_secret` in `api/main.py`) — single-user auth, not multi-tenant. Start command is set explicitly (Railpack doesn't reliably auto-detect FastAPI or read `Procfile`):
```
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```
Requires `api/__init__.py` so `api.main` resolves as a package import.
- **GitHub Actions** (`daily.yml`) runs independently — talks directly to Supabase and Slack, unaffected by frontend/backend deploys.

### Known gotchas
- Next.js App Router caches `fetch()` GET requests by default; `lib/api.ts`'s data-fetching functions use `{ cache: "no-store" }` so `router.refresh()` pulls fresh data after any status-changing action.
- CORS origin matching is exact-string — a trailing slash mismatch between `FRONTEND_URL` and the browser's `Origin` header fails preflight.
- `/health` is excluded from the `API_SECRET` check (separate unauthenticated router), since Railway's health probe doesn't send `x-api-key`.
- The Next.js proxy does a straight path/method/body forward, so any new FastAPI endpoint is reachable at the matching `/api/...` path with no proxy changes — only `lib/api.ts` needs a new function.

## Automation

`.github/workflows/daily.yml` runs `collect_github.py` then `slack_report.py` once a day (~12pm Central). Can also be triggered manually from the Actions tab.

## The dashboard (Next.js + FastAPI)

FastAPI wraps `db_tools.py` behind REST endpoints (all gated by `API_SECRET` except `/health`):
- `GET /jobs` — search/filter postings (`status`, `min_score`, `company`, `location`, `source`, `title`, posted/scraped date ranges, `limit`), backed by `search_jobs()`
- `PATCH /jobs/status` — update a posting's status, backed by `mark_status()`
- `GET /metrics` — status counts, backed by `get_status_counts()`
- `GET /history` — weekly status-history snapshots, backed by `get_status_history_weekly()`
- `PATCH /jobs/not-interested` — marks a posting "not interested" (status + score reset), backed by `mark_not_interested()`
- `POST /chat` — conversational agent, backed by `agent.py`'s `ask_agent()`, exposing two tools:
  - `search_jobs` — filterable by status, min score, company, location, source, title, and posted/scraped date ranges
  - `mark_status` — updates application status
  
The system prompt is rebuilt on every call with the current date (Central time), so relative queries like "posted this week" resolve to real date filters. `ChatWidget.tsx` sends `message` + `conversation_history` and renders returned text plus any jobs via `JobCard`.

All frontend requests go through `lib/api.ts` → same-origin `/api/...` → `app/api/[...path]/route.ts`, which proxies to FastAPI and attaches `API_SECRET` server-side.
 
The frontend renders four pieces, sharing one `lib/statusColors.ts` mapping so colors/labels/order stay in sync:
- **Metrics tiles** (`MetricsTiles.tsx`) — one per status
- **Status-over-time chart** (`StatusChart.tsx`) — Recharts line chart, one line per status, custom tooltip that groups overlapping near-zero values
- **Unapplied jobs list** (`UnappliedJobs.tsx`) — cards with Apply / Mark Applied / Not Interested actions
- **Chat widget** (`ChatWidget.tsx`) — natural-language search and status updates, renders results as `JobCard`s

Pixel-art aesthetic (Press Start 2P headers/buttons, Silkscreen body text, chunky offset drop-shadow borders) in a strawberry-matcha palette — matcha greens for early/neutral statuses, strawberry pinks for interview stages, muted tones for rejected/withdrawn.

## Status / next steps
 
- [x] Multi-source collection with dedup
- [x] Personalized Claude classification
- [x] Slack daily digest
- [x] Full automation via GitHub Actions
- [x] Migrate dashboard from Streamlit to Next.js + FastAPI
- [x] Metrics tiles, status-history chart, unapplied jobs list with mark-applied
- [x] Pixelated strawberry-matcha visual redesign
- [x] Floating chat widget — `agent.py` tool-use agent ported into `ChatWidget.tsx`, wired through `/chat`
- [x] "Not interested" manual filter — `PATCH /jobs/not-interested` + `mark_not_interested()`
- [x] Migrate data layer from Google Sheets to Supabase (Postgres) — `sheet_tools.py` replaced by `db_tools.py`, all consumers repointed and verified
- [x] Deployment — Next.js on Vercel, FastAPI on Railway, verified end-to-end
- [x] Shared-secret API gating — `API_SECRET` on all routes except `/health`, browser routed through the Next.js proxy
- [x] Expanded chat search — `search_jobs` filterable by location, source, title, and posted/scraped date ranges; system prompt injects today's date so relative date queries resolve correctly
- [x] Closed/dead-posting detection — `posting_status()` wired into `collect_github.py`, skips postings before classification/insertion
- [ ] Additional sources (Greenhouse/Lever/Ashby direct pulls, Gmail parsing for LinkedIn/Handshake alerts)
- [ ] Re-enable SimplifyJobs once it adds 2027 postings