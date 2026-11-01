# InternPilot AI — Job Discovery Update

## What's included

- 71 configured employer board endpoints across 69 employer names.
- Public job feeds for Greenhouse, Lever, Ashby, and Workday.
- Concurrent source checks with per-board timeouts and retry handling.
- A failure on one employer does not stop other employers from syncing.
- Stable job IDs and duplicate collapse by employer + posting URL.
- Only postings matching the current tech/student/Canada relevance rules enter the feed.
- A successful board refresh retires listings that disappeared from that exact board. A failed board refresh does **not** delete old jobs.
- Source health is stored and visible to signed-in users through `/api/discover/status`.
- Scheduled refresh starts shortly after backend startup and repeats every 6 hours by default.
- A command-line checker reports which board endpoints currently respond.

## Employer coverage

The configured board inventory includes:

- **Canadian / Toronto-area technology employers:** 1Password, Ada, BenchSci, Cohere, D2L, Deep Genomics, Faire, Float, Geotab, Hootsuite, Jobber, Klue, Loopio, Magnet Forensics, Miovision, Neo Financial, PointClickCare, Shakepay, ShyftLabs, StackAdapt, TELUS Digital, Tenstorrent, Waabi, Wattpad, Wealthsimple.
- **Global technology employers with Canadian roles:** Affirm, Airbnb, Anthropic, Coinbase, Confluent, Databricks, Dropbox, Elastic, GitLab, Instacart, Lyft, MongoDB, NVIDIA, Okta, OpenAI, PagerDuty, Pinterest, Ramp, Reddit, Robinhood, Samsara, Scale AI, Snowflake, Stripe, Tailscale, Twilio.
- **Large Canadian / Ontario employers:** Autodesk, BMO, CIBC, Ciena, Intel, Magna, Manulife, Royal Bank of Canada, Sun Life, TD, Thomson Reuters.
- **Additional software / AI employers:** Cerebras, Clearco, Hopper, Ideogram, Kindred AI, Lightmatter, Thinkific.

The same employer may have more than one configured board (for example, a general and campus Workday board). Therefore, 71 endpoints is not 71 distinct companies.

## Important accuracy note

A configured endpoint is a candidate integration, not a promise that the employer currently has open student jobs. ATS board slugs and endpoints can change, some boards can be empty, and some employers may block or alter public endpoints. The live health check below is the authoritative test from your machine. Do not describe a board as live/healthy until it passes that check.

Greenhouse, Lever, and Ashby are implemented against their documented public job-posting interfaces. Workday is implemented against the employer's public CXS search endpoints. Jobs link to the employer's own posting page; InternPilot does not submit applications.

## Install the update

This ZIP is a full project replacement. Back up your existing project and database before replacing it. Extract the ZIP into your chosen project directory (for example `E:\internpilot-ai`). Do not overwrite your real `.env` file with `.env.example`.

### PowerShell setup

```powershell
cd E:\internpilot-ai\backend
..\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If you are setting it up from a fresh extraction, create the environment first:

```powershell
cd E:\internpilot-ai\backend
py -3.13 -m venv ..\.venv
..\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Keep the existing database and `.env` when upgrading an existing installation. The database migration is additive and adds source health / freshness columns and tables automatically at startup.

### Check the employer endpoints

From `E:\internpilot-ai\backend` with the virtual environment activated:

```powershell
python -m app.check_sources
```

To check one employer only:

```powershell
python -m app.check_sources --company Waabi
```

A successful result means the endpoint responded and its JSON could be read. A healthy board can still have zero postings. Some failures may be temporary (rate limiting, network, or ATS changes); recheck before removing a board from the registry.

### Start the app

Backend terminal:

```powershell
cd E:\internpilot-ai\backend
..\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Frontend terminal:

```powershell
cd E:\internpilot-ai\frontend
npm install
npm run dev
```

Sign in and click **Discover internships** to run the first manual refresh. The scheduler also starts a refresh shortly after the backend starts, then repeats every 6 hours.

## API endpoints

- `POST /api/discover` — manually refresh all configured boards (requires login).
- `GET /api/discover/status` — latest per-board health, count and checked time (requires login).
- `GET /api/health` — basic health plus number of configured sources.

## Scheduler configuration

In `backend/.env`:

```dotenv
ENABLE_JOB_SCHEDULER=true
JOB_SYNC_INTERVAL_HOURS=6
```

Set `ENABLE_JOB_SCHEDULER=false` if you want to run refreshes only manually or through an external scheduler. For a multi-worker production deployment, do not run one in-process scheduler per worker; use a single dedicated scheduler/worker or an external scheduled task to avoid duplicate refreshes.

## Current limits / next work

1. The 71 endpoints need a real health-check run from your Windows machine; this build cannot prove your network can reach every employer endpoint.
2. Current filtering prioritizes technology, student / internship language, and Canada / Ontario locations. Add profile-based location preferences and broader role families after observing false positives/negatives.
3. Some major employers use other ATS platforms (for example SuccessFactors, iCIMS, Oracle, SmartRecruiters, Eightfold, and proprietary systems). They are not included in this release unless a dedicated adapter is implemented and tested.
4. A source outage can leave old listings visible until a successful refresh occurs. The app preserves them intentionally rather than risking data loss; the source health panel shows the failure.
5. Before public launch, move refresh work to a background worker, add monitoring/alerts, test restore behavior, and verify employer terms / request limits.

## API documentation and board inventory references

- Greenhouse public Job Board API: https://docs.greenhouse.io/job-board
- Lever public Postings API: https://github.com/lever/postings-api
- Ashby public Job Postings API: https://developers.ashbyhq.com/docs/public-job-posting-api
- Public Canadian internship employer-board inventory used as a starting point for company/ATS discovery (not a substitute for this project's own live health check): https://github.com/krishi-shah/Toronto-AI-ML-internship-radar/blob/main/companies.py
