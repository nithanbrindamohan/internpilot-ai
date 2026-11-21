# InternPilot AI — Bulk applications (Phase 1)

This update adds **bulk draft preparation and explicit employer-site handoff**, not automatic third-party submissions.

## What works

- Select up to 10 jobs and create application drafts in one request.
- Existing drafts are reused, not duplicated.
- Select up to 10 saved applications and explicitly confirm review before employer-site handoff.
- Employer posting URLs are checked for HTTPS and returned for user-initiated opening.
- The tracker labels `needs_manual_submission` and `user_reported_submitted` separately. Neither is a verified receipt from an employer.
- Batch operations are restricted to the signed-in user's own applications.
- Existing SQLite databases receive **additive** columns when the backend starts; no manual database reset is needed.
- No private resume is sent to any external service and no external application is submitted automatically.

## Install (PowerShell)

1. Back up your source code and database locally before updating the application. **Do not upload database backups or secrets to GitHub.**
2. Extract this ZIP **into `E:\internpilot-ai`** using PowerShell:

   ```powershell
   Expand-Archive -LiteralPath "$HOME\Downloads\internpilot-bulk-apply-phase1.zip" -DestinationPath 'E:\internpilot-ai' -Force
   ```

   The ZIP contains paths `backend/app/...` and `frontend/src/...` rooted at the project directory.
3. Restart the FastAPI backend and Vite frontend. The backend will apply safe, additive SQLite migrations during startup.
4. Run the isolated tests:

   ```powershell
   cd E:\internpilot-ai\backend
   python -m pip install pytest httpx
   python -m pytest tests/test_bulk_apply.py -v
   ```

5. Test with a small number of **test postings** before inviting real users to use this feature.

## API endpoints

- `POST /api/applications/bulk` — `{ "job_ids": ["job-id-1", "job-id-2"] }` (drafts only)
- `POST /api/applications/bulk/handoff` — `{ "application_ids": [1, 2], "confirm_reviewed": true }` (returns HTTPS posting links, marks awaiting manual submission)
- `GET /api/applications` — now includes `submission_state`, `submission_method`, and `approved_at`

## Requirements for real automatic submission (Phase 2)

The application currently indexes postings from Greenhouse, Lever, Ashby, and Workday. **Reading their public job listings does not authorize posting applications.** For actual direct integration you need employer/partner authorization, credentials where the ATS requires them, the specific posting's submission form schema and required custom questions, consent to disclose each applicant's resume and profile, handling of CAPTCHA or other anti-bot requirements, safe queuing and retry rules, and confirmed receipts. The current app stores the uploaded resume under a random name but does not save a lookup key for a later employer attachment; this must be addressed before direct submission. A verified provider should be added individually and tested against authorized sandbox accounts, not generic HTML form scraping.

### Protection rules for Phase 2

- Only accept explicit, per-application user approval.
- Never assume submission succeeded from an HTTP timeout.
- Never auto-retry uncertain submissions without idempotency/receipt verification.
- Validate and sanitize form data; do not invent qualifications.
- Do not bypass CAPTCHA, access controls, or application-site restrictions.
- Record provider response IDs and submission timestamp, and permit users to withdraw approval.
- Keep provider keys on the server in secret storage, never in frontend JavaScript or GitHub.

## Validation performed

On the supplied **source-only** project snapshot, isolated pytest test cases for creation, deduplication, privacy, handoff approval, and submission-state labeling passed (2 tests). Browser tests and real employer submissions were **not** executed; run the frontend build and Playwright tests on your machine.
