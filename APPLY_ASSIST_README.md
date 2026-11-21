# InternPilot AI — Application Review & Browser Assist (beta)

This patch is built on the **GTA Engineering Filters + Bulk Apply Phase 1** source version. It **does not send applications** to employers. It adds a review workspace, per-user application answers, a downloadable JSON packet, and a local optional Playwright helper to prefill common form fields while a user watches.

## Install

1. Back up or commit your source first. Extract this ZIP at `E:\internpilot-ai`, keeping the `backend/` and `frontend/` folder structure. It **overwrites** `backend/app/main.py`, `backend/app/db.py`, `frontend/src/main.jsx`, and `frontend/src/style.css`. If you have edited these since the GTA patch, merge changes rather than overwrite.
2. Restart backend and frontend. The backend automatically creates the additive `applications.answers_json` column on startup. It does not delete existing applications.
3. In **Application Tracker**, click **Review & prepare**. Check applicant information; generate/edit a tailored cover letter; fill common answers; **Save reviewed packet**.
4. Click **Download application packet** to save a local JSON copy for the optional browser helper. This file contains your name, email, cover letter and answers. **Do not commit it to GitHub or send it to others.** Delete it when finished.
5. Open **Open employer application** for normal manual completion, or use the optional autofill helper below.

## Optional local browser autofill

From a PowerShell terminal:

```powershell
cd E:\internpilot-ai\frontend
npm install --save-dev @playwright/test
npx playwright install chromium
node .\scripts\review-autofill.mjs "$HOME\Downloads\internpilot-application-1.json" --resume "C:\path\to\your\resume.pdf"
```

Replace the example packet filename with the actual downloaded file and the resume with its real local path. If no resume file is available, omit `--resume`.

The helper opens the HTTPS link, **pauses so you can navigate to the actual employer form**, fills only recognizable fields (name/email/phone/social link/cover letter), optionally attaches your explicitly specified resume, and **stops before submission**. Employer forms differ widely and may use embedded frames, multi-step workflows, custom React widgets, questionnaires, logins, human verification or inaccessible fields. These **are not auto-completed**. Inspect every field, answer every required question, and click the employer's Submit button yourself. Never bypass CAPTCHAs, anti-bot measures, or employer terms.

## Limitations and privacy

- This is assisted form prefill, not guaranteed one-click full application. Automated submissions and authenticated ATS integrations are **not implemented**.
- The app still **does not retain an original resume upload reference** usable for automatic attachment, so the helper accepts a local `--resume` file path instead.
- The packet endpoint requires the signed-in user and does not return raw resume text or account secrets. It returns applicant personal data, so downloaded packets are sensitive.
- The current app's shared `jobs` table still contains legacy AI score fields written by `/api/jobs/{id}/ai-match`; fix per-user score persistence before a multi-user launch.
- A reviewed packet is not a verified submission. Mark an application Submitted only after receipt from the employer.
- Do not commit downloaded packets or resumes. Add `internpilot-application-*.json` to your project `.gitignore` if you use the helper.

## Quick checks

```powershell
cd E:\internpilot-ai\backend
python -m pytest tests/test_apply_assist.py -v
cd E:\internpilot-ai\frontend
npm run build
```
