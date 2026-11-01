# InternPilot AI — development roadmap

## Current build
- Open to users from any school/background, but registration requires a code you personally generate.
- Each invitation code is single-use; existing users can log in without another code.
- Individual accounts have private profiles, resume text, and application trackers.
- Job discovery includes 71 configured public board endpoints across 69 employer names using Greenhouse, Lever, Ashby, and Workday adapters.
- Sources refresh shortly after backend startup and every 6 hours by default; users can also refresh manually.
- Per-board health and sync timestamps are recorded. A source failure does not delete its previous jobs; listings are retired only after a successful refresh no longer returns them.
- AI matching and cover-letter drafting use the backend OpenAI API key when configured.
- Applications are not submitted automatically.

## Run locally (Windows PowerShell)

1. Extract this folder to `E:\internpilot-ai` (or another path).
2. Backend setup, in a new PowerShell window:

```powershell
cd E:\internpilot-ai\backend
py -3.13 -m venv ..\.venv
..\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

3. Open `backend\.env` and set a long random `TOKEN_SECRET`. Add `OPENAI_API_KEY` for AI features. Keep both values private and only in the backend `.env` file.
4. Start backend:

```powershell
cd E:\internpilot-ai\backend
..\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

5. In a second PowerShell window, start frontend:

```powershell
cd E:\internpilot-ai\frontend
npm install
npm run dev
```

6. Open `http://localhost:5173`.
7. Generate your own invitation code in another PowerShell window:

```powershell
cd E:\internpilot-ai\backend
..\.venv\Scripts\Activate.ps1
python -m app.create_invite --count 1
```

8. Register with that code. Keep it private; it can only create one account.

## Before calling it production-ready

### Priority 1 — correctness and security
- Add automated backend tests for registration, login, invite reuse, simultaneous code redemption, account isolation, resume upload, and application ownership.
- Add email verification, password reset, login throttling/rate limits, abuse monitoring, and admin-only invite management.
- Replace browser `localStorage` bearer-token storage with secure HttpOnly, SameSite cookies or a carefully reviewed equivalent; add CSRF/XSS protections.
- Validate upload content/type and size, scan uploads, store them outside the web root, and enforce private access controls.
- Add account deletion, data export, privacy policy, terms, and a clear resume/data retention policy.
- Review authorization on every endpoint; never trust user IDs supplied by the browser.

### Priority 2 — reliable infrastructure
- Move SQLite to managed PostgreSQL before multi-user cloud deployment.
- Move local resume files to private object storage with signed, short-lived access URLs.
- Configure HTTPS, production secrets, strict CORS, backups, restore testing, logs, monitoring, and error alerts.
- Add CI checks, dependency/security scanning, database migrations, and staging deployment.

### Priority 3 — useful job data
- Run `python -m app.check_sources` from the backend directory on the actual Windows machine. The list is configured, but each endpoint still needs runtime verification from your network.
- Investigate failed boards individually; ATS slugs and endpoints can change, and an empty board is not necessarily a failed integration.
- Expand to SuccessFactors, iCIMS, SmartRecruiters, Oracle, Eightfold, and proprietary career sites only after building and testing dedicated adapters.
- Improve location, remote-work, eligibility, work-authorization, and job-family filters based on real user feedback.
- Add source monitoring/alerts and an external single-worker scheduler before multi-worker production deployment.
- Never claim a job is current unless its source has been checked recently.

### Priority 4 — product quality
- Test mobile/responsive layouts and accessibility.
- Add onboarding, profile completion guidance, clear error states, and user feedback.
- Let users edit AI output and clearly label generated content; never submit applications automatically.
- Add analytics that respect privacy and do not collect resume contents unnecessarily.

## Definition of “working 100%”
No software can be guaranteed 100% bug-free. A sensible launch gate is: all critical automated tests pass; security review is complete; backups and restore are tested; job sources are verified; monitoring and support processes exist; privacy/legal pages are published; and a small private beta runs successfully before wider release.

## Important limitations of this MVP
- The current project is intended for local development and testing.
- 71 board endpoints are configured, but they have not all been live-checked from your Windows computer. Run `python -m app.check_sources` and review the per-board results.
- The current adapters cover Greenhouse, Lever, Ashby, and Workday. Other ATS platforms are not yet integrated.
- SQLite and local resume storage are not suitable for a scaled public deployment.
- Scheduled refresh currently runs inside the API process; use one dedicated worker or an external scheduler in production.
- No automatic application submission is implemented.

## Job discovery update quick test

From `E:\internpilot-ai\backend` with the virtual environment activated:

```powershell
python -m app.check_sources
python -m unittest discover -s tests -v
```

The included adapter and sync-safety tests should pass. The health check contacts the real public job-board endpoints and may take a few minutes.
