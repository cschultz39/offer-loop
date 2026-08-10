# Job Search Agent

An automated pipeline that collects new-grad Software Engineering / Forward Deployed Engineer job postings, filters and scores them against personal preferences using Claude, tracks them in a Supabase (Postgres) database, and provides a Next.js dashboard (backed by a FastAPI service) to browse postings and manage application status — with a daily Slack digest of new postings.

Built as a personal tool to reduce the manual overhead of a new-grad job search (target: Summer/Fall 2027 start), and as a hands-on project in building agentic tools with the Claude API and a full-stack web app.

## Architecture overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Data sources   │ --> │  Collector       │ --> │  Supabase       │
│  (GitHub repos) │     │  (collect_github │     │  (Postgres,     │
│                 │     │  .py)            │     │  single source  │
│                 │     │                  │     │  of truth)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                 │                          │
                                 v                          v
                         ┌──────────────────┐     ┌─────────────────┐
                         │  Claude API      │     │  Slack digest   │
                         │  classification  │     │  (slack_report  │
                         │ (relevance score)│     │  .py)           │
                         └──────────────────┘     └─────────────────┘

                         ┌──────────────────────────────────────────┐
                         │  FastAPI backend                         │
                         │  Wraps agent.py / sheet_tools.py logic   │
                         │  via /jobs, /jobs/status, /metrics,      │
                         │  /history, /chat endpoints               │
                         └──────────────────────────────────────────┘
                                          │
                                          v
                         ┌──────────────────────────────────────────┐
                         │  Next.js + Tailwind dashboard            │
                         │  Metrics tiles, status-over-time chart,  │
                         │  unapplied jobs list — pixelated UI      │
                         │  in a strawberry matcha color palette    |
                         └──────────────────────────────────────────┘

         Everything in the collection pipeline is run daily,
         automatically, via GitHub Actions (.github/workflows/daily.yml)
```

**Note:** the dashboard was originally built in Streamlit (`dashboard.py` + `agent.py`'s chat-based tool-use agent). It has since been migrated to a Next.js + Tailwind frontend with a FastAPI backend, due to Streamlit's CSS/layout limitations and slow (10-15s) full-script reruns on every interaction. `dashboard.py` is retained for reference only; `agent.py`'s tool-use logic is now the active backend for the `/chat` endpoint, called from `ChatWidget.tsx` on the Next.js side. The data layer has also since migrated from Google Sheets to a Supabase (Postgres) database — see `db_tools.py`, which replaced `sheet_tools.py`.

## What it does

1. **Collects** active new-grad SWE postings from curated GitHub repos (currently `speedyapply/2027-SWE-College-Jobs`; `SimplifyJobs/New-Grad-Positions` is supported but disabled until it adds 2027 postings)
2. **Filters** by title keywords (software engineer, backend, frontend, forward deployed, etc.) and active/visible status
3. **Deduplicates** against what's already been collected (checked via `id` lookups and canonicalized-link comparison in Supabase, so the same posting reachable through different sources/query strings doesn't create duplicate rows)
4. **Fetches** the full posting text for anything that isn't a name-based dealbreaker, via `fetch_job_text.py`'s `JobTextFetcher` — tries a direct ATS JSON API first (`ats_apis.py`, for Greenhouse and most Workday tenants), falls back to Playwright for JS-rendered boards (Ashby, remaining Workday, Meta Careers, Workable, iCIMS, Dayforce), and plain `requests`/BeautifulSoup otherwise. Postings that come back dead (fetch failed) or closed (page text says so) are skipped entirely — never classified, never written to the database.
5. **Classifies** each remaining new posting with the Claude API against personal preferences — location tiers, grad-year match (2027 preferred, 2026 excluded), Python/AI-agent/LLM-usage signal, and hard-excludes for defense/government contractors and companies associated with ICE/surveillance work (checked via an explicit blocklist before the Claude call, so those postings skip both the fetch step and the API call entirely)
6. **Stores** everything in a Supabase Postgres database — a `job_postings` table (id, company, title, location, link, source, date posted, date scraped, status, relevance score, relevance reason) plus a `status_history` table logging every status transition as an event (job_id, old_status, new_status, timestamp)
7. **Reports** newly found postings to Slack once a day, sorted by relevance score
8. **Runs automatically** every day via a GitHub Actions scheduled workflow — no manual steps required
9. **Serves a dashboard** (Next.js frontend + FastAPI backend) showing status count tiles, a weekly status-history line chart (one line per status, color-matched to its tile), and the top 10 unapplied jobs with one-click "mark applied"

## File structure

```
job-search-agent/
├── collect_github.py          # Main collector: fetch, filter, dedup, fetch text, classify, write to sheet
├── fetch_job_text.py           # JobTextFetcher — routes posting-page text extraction between direct ATS APIs (ats_apis.py), Playwright, and requests/BeautifulSoup
├── ats_apis.py                  # Direct JSON API access for Greenhouse and Workday, bypassing browser rendering where the platform allows it
├── db_tools.py                 # Shared Supabase (Postgres) read/write logic (used by API + collector)
├── slack_report.py             # Formats and sends today's new postings to Slack
├── reclassify.py               # One-off batch re-classification of existing rows
├── check_extraction.py         # Standalone diagnostic: buckets extraction quality (good/thin/closed/blocked/dead) across all saved postings, used to find routing gaps
├── agent.py                    # Claude tool-use agent: search_jobs / mark_status tools (currently unused by the active UI — see note above)
├── dashboard.py                # Legacy Streamlit chat UI (superseded — see note above)
├── sources/
│   ├── __init__.py
│   ├── simplifyjobs.py         # SimplifyJobs source (currently disabled — 2026 postings only)
│   └── speedyapply.py          # speedyapply 2027-SWE-College-Jobs source
│   └── newgrad2027.py          # vanshb03/New-Grad-2027 source
├── api/                         # FastAPI backend
│   ├── __init__.py              # Makes api/ importable as a package — required for Railway's `uvicorn api.main:app` start command
│   └── main.py                  # /jobs, /jobs/status, /metrics, /history, /chat endpoints
├── frontend/                    # Next.js + Tailwind dashboard
│   ├── app/
│   │   ├── layout.tsx            # Root layout — loads Pixelify Sans + Press Start 2P fonts
│   │   ├── page.tsx              # Main dashboard page
│   │   └── globals.css           # Strawberry matcha color tokens, pixel-art tile/card styles
│   ├── components/
│   │   ├── MetricsTiles.tsx      # Status count tiles, colors sourced from lib/statusColors.ts
│   │   ├── StatusChart.tsx       # Weekly status-history chart (Recharts), one line per status
│   │   ├── UnappliedJobs.tsx     # Scrollable unapplied jobs list, renders JobCard per job
│   │   ├── JobCard.tsx           # Shared job card: apply link, Mark Applied, Not Interested buttons
│   │   └── ChatWidget.tsx        # Floating chat widget: talks to /chat, renders JobCard for returned jobs
│   └── lib/
│       ├── api.ts                # Fetch wrappers for the FastAPI backend
│       └── statusColors.ts       # Single source of truth for status -> color/label mapping
├── .github/workflows/
│   └── daily.yml                 # Scheduled automation (runs collector + Slack report daily)
├── requirements.txt              # Single consolidated dependency list (collector + Slack report + FastAPI backend all share one file/venv, since Railway builds from repo root)
├── .env                          # Local secrets (not committed)
├── service_account.json          # Google service account credentials (not committed)
└── .gitignore
```

## Data sources

| Source | Status | Notes |
|---|---|---|
| `speedyapply/2027-SWE-College-Jobs` | Active | Markdown tables (HTML-formatted cells), parsed via `sources/speedyapply.py` |
| `vanshb03/New-Grad-2027` | Active | Markdown table (HTML-formatted cells, `**bold**` company names, `<br>`-separated multi-location cells), parsed via `sources/newgrad2027.py`. Filters out 🔒 (closed) postings and anything dated before 2026-07-24 (pre-2027-cycle postings) |
| `SimplifyJobs/New-Grad-Positions` | Disabled | Clean JSON backing (`listings.json`), but currently only has 2026 grad postings — re-enable once 2027 roles are added |

## Classification logic

Each new posting is sent to the Claude API with the candidate's preferences embedded in the prompt:
- **Location**, ranked: Chicago > Chicagoland Area > Big Cities in the Midwest > Portland/Washington > anywhere in the USA
- **No preference** on company type/size (big tech, startup, quant/finance all acceptable)
- **Hard dealbreakers** (always scored 1, marked not relevant):
  - Defense contractors / government-sector roles / clearance-required roles
  - Companies associated with ICE, immigration enforcement, or public/mass surveillance (checked first against an explicit blocklist for efficiency and reliability, with the Claude prompt as a fallback for companies not yet on the list)

Dealbreaker postings are currently still written to the sheet (visible, scored low) rather than excluded outright, so classification accuracy can be sanity-checked. A future dashboard update should filter these out of default views.

## Environment variables / secrets

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API access (classification + agent) |
| `GH_TOKEN_PAT` | GitHub API token (higher rate limits; named to avoid GitHub Actions' reserved `GITHUB_*` prefix) |
| `SLACK_WEBHOOK_URL` | Incoming webhook for the daily Slack digest |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key (server-side only — used by the collector, Slack report, and FastAPI backend, never exposed to the frontend) |
| `NEXT_PUBLIC_API_URL` | Base URL the frontend uses to reach the FastAPI backend |
| `FRONTEND_URL` | Live Vercel domain, used for CORS in `api/main.py` |

Locally, the Python-side variables live in `.env`. In GitHub Actions, they're stored as repository secrets and injected as environment variables in the workflow.

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

- **Frontend**: Next.js on Vercel. Root Directory set to `frontend`; `NEXT_PUBLIC_API_URL` points at the Railway backend URL.
- **Backend**: FastAPI on Railway. Root Directory is the **repo root** (not `api/`) — `api/main.py` imports `db_tools.py` from the parent directory via `sys.path.append`, and the consolidated `requirements.txt` also lives at the repo root, so both need to be in the build context. Railway's start command is set explicitly (Railpack doesn't reliably auto-detect FastAPI or read `Procfile`):
```
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```
This requires `api/__init__.py` to exist so `api.main` resolves as a package import.
- **GitHub Actions** (`daily.yml`) runs independently of both — it talks directly to Supabase and Slack, unaffected by frontend/backend deploys.

### Known gotchas from getting this working
- Next.js App Router caches `fetch()` GET requests by default; the dashboard's data-fetching functions in `lib/api.ts` (`getMetrics`, `getWeeklyHistory`, `getUnappliedJobs`) use `{ cache: "no-store" }` so `router.refresh()` (called after any status-changing action, including agent-driven ones from chat) actually pulls fresh data instead of a stale cached response.
- CORS origin matching is exact-string — a trailing slash mismatch between `FRONTEND_URL` and the browser's actual `Origin` header is enough to fail preflight on `/chat` and `/jobs/status`.

## Automation

`.github/workflows/daily.yml` runs `collect_github.py` then `slack_report.py` automatically once a day (currently scheduled ~12pm Central, adjusted for UTC in the cron expression). Can also be triggered manually from the Actions tab in GitHub.

## The dashboard (Next.js + FastAPI)

The FastAPI backend wraps the existing `db_tools.py` logic behind REST endpoints:
- `GET /jobs` — search/filter postings (`status`, `min_score`, `company`, `limit`), backed by `search_jobs()`
- `PATCH /jobs/status` — update a posting's status (`job_id`, `new_status`), backed by `mark_status()`, validated against the same fixed status set used throughout the sheet
- `GET /metrics` — status counts, backed by `get_status_counts()`
- `GET /history` — weekly status-history snapshots, backed by `get_status_history_weekly()`
- `PATCH /jobs/not-interested` — marks a posting "not interested" (sets status, score to 1, and a fixed reason), backed by `mark_not_interested()`
- `POST /chat` — conversational agent endpoint, backed by `agent.py`'s `ask_agent()` (search_jobs / mark_status tools); `ChatWidget.tsx` sends `message` + `conversation_history` and renders returned text plus any jobs via `JobCard`

The Next.js frontend renders three main pieces, all sharing a single `lib/statusColors.ts` mapping so colors, labels, and status order can never drift out of sync across components:
- **Metrics tiles** (`MetricsTiles.tsx`) — one tile per status, full-width row across the top
- **Status-over-time chart** (`StatusChart.tsx`) — Recharts line chart, one step-line per status, each colored to match its tile, with a custom tooltip that shows only the hovered status (or a small cluster of statuses within ~10 counts of each other, to handle overlapping zero-value dots)
- **Unapplied jobs list** (`UnappliedJobs.tsx`) — scrollable card matching the chart's height, each entry rendered via `JobCard.tsx` with "Apply here", "Mark applied", and "Not interested" buttons
- **Floating chat widget** (`ChatWidget.tsx`) — bottom-right toggle button opens a chat panel; sends messages to `/chat`, maintains conversation history client-side, and renders any returned jobs (excluding already-applied ones) as `JobCard`s with the same applied/not-interested actions

The UI uses a pixel-art aesthetic (Press Start 2P for headers/tile numbers/buttons, Silkscreen for body text, chunky offset drop-shadow borders instead of soft shadows) in a strawberry-matcha color palette — matcha greens for early/neutral statuses, strawberry pinks for interview stages, muted desaturated tones for rejected/withdrawn.

## Status / next steps

- [x] Multi-source collection with dedup
- [x] Personalized Claude classification
- [x] Google Sheets storage
- [x] Slack daily digest
- [x] Full automation via GitHub Actions
- [x] Migrate dashboard from Streamlit to Next.js + FastAPI
- [x] Metrics tiles, status-history chart, unapplied jobs list with mark-applied
- [x] Pixelated strawberry-matcha visual redesign
- [x] **Floating chat widget** — `agent.py` tool-use agent (search_jobs / mark_status) ported into `ChatWidget.tsx`, wired through `/chat`, styled to match the pixel-art theme
- [x] **"Not interested" manual filter** — `PATCH /jobs/not-interested` + `mark_not_interested()`, exposed via a button on `JobCard.tsx` (used in both the unapplied list and chat results)
- [x] **Migrate data layer from Google Sheets to Supabase (Postgres)** — schema created, data migrated via `migrate_to_supabase.py`, `sheet_tools.py` replaced by `db_tools.py` (using `supabase-py`), collector/Slack report/FastAPI/agent all repointed; verified working end-to-end
- [x] **Deployment** — Next.js on Vercel, FastAPI on Railway; both live and verified end-to-end (metrics/history/jobs load, mark-applied and mark-not-interested persist and reflect immediately, chat agent reachable and its status updates also reflect immediately)
- [ ] Additional sources (Greenhouse/Lever/Ashby direct pulls, Gmail parsing for LinkedIn/Handshake alerts)
- [ ] Re-enable SimplifyJobs once it adds 2027 postings