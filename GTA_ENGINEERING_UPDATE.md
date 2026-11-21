# InternPilot AI — Toronto/GTA Engineering Discovery + Filters

## What this update changes

- Expands discovery matching from mainly software/AI to mechanical, electrical, civil, mechatronics, manufacturing, robotics, chemical, aerospace and general engineering internships/co-ops.
- Adds **candidate public job feeds** for Toronto/GTA employers on Ashby and Lever, including Kepler Communications, Human Computer Lab, Trexo Robotics, General Magic, Micromart, Bree, and others. Boards are **not guaranteed live**; the existing per-source health monitoring reports errors and counts. **No jobs are invented or inserted manually**.
- Adds backend `GET /api/jobs` filters `region`, `city`, `discipline`, `work_mode`, `term`, while preserving `q` and `min_score`.
- Defaults the opportunity feed to Toronto & GTA; adds city, engineering field, remote/hybrid/on-site, and internship term dropdowns.
- Shows employer location and parsed `Start: ...` in each job card. If no explicit term can be identified in the title or relevant description, it says `Not specified`. A season/term is **not an exact start date**.
- Stops returning shared `jobs.ai_match_score` / AI explanation through job listings. **This does not yet fix the shared persistence on the AI match endpoint**; Phase 1 security work should still move user-specific AI results into per-user storage.

## Install safely (Windows PowerShell)

**Requires the Bulk Apply Phase 1 update already installed.** This patch is based on that version of `backend/app/main.py` and `frontend/src/main.jsx`; merging is needed if you have newer local changes.

1. Back up the project source and check the worktree, especially if collaborating via Git:

   ```powershell
   cd E:\internpilot-ai
   git status
   git switch -c feature/gta-engineering-filters
   ```

2. Download `internpilot-gta-engineering-filters.zip` to Downloads. Then extract from the **project root**:

   ```powershell
   cd E:\internpilot-ai
   Expand-Archive -LiteralPath "$HOME\Downloads\internpilot-gta-engineering-filters.zip" -DestinationPath "E:\internpilot-ai" -Force
   ```

3. Restart both servers. From backend, run tests:

   ```powershell
   cd E:\internpilot-ai\backend
   python -m pytest tests/test_gta_filters.py tests/test_bulk_apply.py -v
   ```

4. From the frontend, run:

   ```powershell
   cd E:\internpilot-ai\frontend
   npm run build
   npx playwright test
   ```

5. Sign in and click **Discover internships**. The refresh makes outbound requests to configured public employer feeds and may take some time. Check `/api/discover/status` (requires login) to see which sources were healthy. Use the new filters in the opportunity feed.

## Tested in the build environment

- 8 backend tests passed in `test_gta_filters.py` and `test_bulk_apply.py` (6 new/updated GTA tests and 2 existing bulk tests).
- Browser build/Playwright **not executed** in this environment; run them locally as shown above.
- When running the original full backend tests, one original `test_sources.py` assertion failed because it expects the literal date `2026-10-31` for a simulated `Posted Today` value. That pre-existing test should be changed to derive the expected date dynamically. It does **not** indicate a failure in the new filters.

## Known limits

- Location is inferred from the location text returned by the provider. Some postings list multiple locations; a posting is GTA if it mentions a GTA location, even if it also lists another region.
- The selected **GTA city** filters only against explicitly listed city names; posting records that say only `GTA` or `Greater Toronto Area` will not match a single-city filter.
- Discipline assignment is rule based, prioritizing title keywords. Some engineering postings are multi-disciplinary or may be categorized under `General Engineering` or `Other`.
- `work_mode` appears as `Not specified` when the source does not give a clear indication. A company being in Toronto does not imply on-site work.
- An employer's public discovery board may be unreachable or empty, and configured boards do not guarantee current internship vacancies.
- Starting term extraction reflects **text in a posting**, not a confirmed contractual start date; always verify the official employer posting.
- The backend currently scans the active jobs table and filters in Python, which is acceptable for a small beta but will need pagination/indexed metadata for a larger dataset.
- No automated application submission is implemented by this update. Phase 2 requires valid authorization for provider submission integrations and user approval.

## Files in this update

- `backend/app/job_filters.py` (new)
- `backend/app/matching.py`
- `backend/app/sources.py`
- `backend/app/main.py`
- `backend/tests/test_gta_filters.py` (new)
- `frontend/src/main.jsx`
- `frontend/src/style.css`
