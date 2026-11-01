import json
import os
import re
import secrets
import hashlib
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:  # Manual refresh still works; install requirements for scheduled refresh.
    BackgroundScheduler = None

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from .db import connect, init_db
from .sources import discover_jobs, source_inventory
from .matching import score_job, is_relevant
from .auth import hash_password, verify_password, create_token, current_user

app = FastAPI(title="InternPilot AI", version="0.2.0")
origins = [x.strip() for x in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(Path(__file__).resolve().parents[1] / "private_uploads")))
MAX_RESUME_BYTES = 5 * 1024 * 1024
_scheduler = None
_sync_lock = threading.Lock()


def sync_job_sources():
    """Refresh every source independently; retire stale jobs only for boards
    that completed successfully, so a temporary outage never wipes listings.
    """
    if not _sync_lock.acquire(blocking=False):
        return {"status": "already_running", "message": "A job refresh is already running."}
    try:
        found, errors, statuses = discover_jobs()
        relevant = [job for job in found if is_relevant(job)]
        now = datetime.now(timezone.utc).isoformat()
        with connect() as db:
            for status in statuses:
                if status["success"]:
                    # Only retire postings from this exact board after a good response.
                    db.execute("UPDATE jobs SET is_active=0 WHERE source_key=?", (status["source_key"],))
                db.execute("""INSERT INTO source_syncs
                    (source_key,company,source,success,jobs_found,checked_at,error)
                    VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(source_key) DO UPDATE SET company=excluded.company,
                    source=excluded.source,success=excluded.success,jobs_found=excluded.jobs_found,
                    checked_at=excluded.checked_at,error=excluded.error""",
                    (status["source_key"], status["company"], status["source"],
                     int(status["success"]), status["jobs_found"], status["checked_at"], status["error"]))
            for job in relevant:
                db.execute("""INSERT INTO jobs
                    (id,source,company,title,location,url,description,posted_at,employment_type,
                     source_key,last_seen_at,is_active,match_score)
                    VALUES (:id,:source,:company,:title,:location,:url,:description,:posted_at,
                            :employment_type,:source_key,:last_seen_at,1,0)
                    ON CONFLICT(id) DO UPDATE SET source=excluded.source,company=excluded.company,
                    title=excluded.title,location=excluded.location,url=excluded.url,
                    description=excluded.description,posted_at=excluded.posted_at,
                    employment_type=excluded.employment_type,source_key=excluded.source_key,
                    last_seen_at=excluded.last_seen_at,is_active=1""",
                    {**job, "last_seen_at": now})
        healthy = sum(1 for status in statuses if status["success"])
        return {"status": "completed", "found": len(found), "relevant": len(relevant),
                "configured_sources": len(statuses), "successful_sources": healthy,
                "failed_sources": len(statuses) - healthy, "errors": errors,
                "checked_at": now, "message": "Job discovery refresh completed."}
    finally:
        _sync_lock.release()


@app.on_event("startup")
def startup():
    global _scheduler
    init_db()
    if os.getenv("ENABLE_JOB_SCHEDULER", "true").lower() in {"1", "true", "yes", "on"} and BackgroundScheduler:
        interval = max(1, int(os.getenv("JOB_SYNC_INTERVAL_HOURS", "6")))
        _scheduler = BackgroundScheduler(timezone="UTC")
        _scheduler.add_job(sync_job_sources, "interval", hours=interval, id="employer-job-sync",
                           next_run_time=datetime.now(timezone.utc) + timedelta(seconds=15),
                           max_instances=1, coalesce=True, replace_existing=True)
        _scheduler.start()


@app.on_event("shutdown")
def shutdown():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None

class RegisterPayload(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    invite_code: str = Field(min_length=8, max_length=64)
    program: str = Field(default="", max_length=120)
    graduation_year: str = Field(default="", max_length=10)

class LoginPayload(BaseModel):
    email: EmailStr
    password: str

class ProfilePayload(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    university: str = Field(default="", max_length=120)
    program: str = Field(default="", max_length=120)
    graduation_year: str = Field(default="", max_length=10)
    location: str = Field(default="Toronto, Ontario", max_length=120)
    work_authorization: str = Field(default="", max_length=200)
    skills: list[str] = Field(default_factory=list, max_length=60)

class ApplicationCreate(BaseModel):
    job_id: str
    cover_letter: str = ""
    notes: str = ""

class ApplicationUpdate(BaseModel):
    status: str

def user_record(user_id: int):
    with connect() as db:
        row = db.execute("""SELECT id,email,full_name,university,program,graduation_year,
            location,work_authorization,skills,resume_filename,created_at FROM users WHERE id=?""",
            (user_id,)).fetchone()
    if not row:
        raise HTTPException(401, "Account not found. Please sign in again.")
    result = dict(row)
    result["skills"] = json.loads(result["skills"] or "[]")
    result["has_resume"] = bool(result.pop("resume_filename"))
    return result

def full_profile(user_id: int):
    with connect() as db:
        row = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(401, "Account not found.")
    result = dict(row)
    result["skills"] = json.loads(result.get("skills") or "[]")
    return result

def extract_resume(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        return content.decode("utf-8", errors="replace")
    if suffix == ".pdf":
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        from docx import Document
        import io
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)
    raise HTTPException(400, "Upload a PDF, DOCX, or TXT resume.")

@app.get("/api/health")
def health():
    return {"status": "ok", "audience": "invite-only users",
            "configured_job_sources": len(source_inventory())}

@app.post("/api/auth/register")
def register(payload: RegisterPayload):
    email = payload.email.lower().strip()
    normalized_code = payload.invite_code.strip().upper().replace("-", "").replace(" ", "")
    code_hash = hashlib.sha256(normalized_code.encode("utf-8")).hexdigest()
    with connect() as db:
        # Consume a code and create the account in the same transaction so a code
        # cannot be used twice by simultaneous registration requests.
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            raise HTTPException(409, "An account with this email already exists.")
        invite = db.execute(
            "SELECT code_hash FROM invite_codes WHERE code_hash=? AND used_at IS NULL",
            (code_hash,)
        ).fetchone()
        if not invite:
            raise HTTPException(403, "This invitation code is invalid or has already been used. Ask the site owner for a new code.")
        cur = db.execute("""INSERT INTO users(email,password_hash,full_name,program,graduation_year)
            VALUES(?,?,?,?,?)""",
            (email, hash_password(payload.password), payload.full_name.strip(),
             payload.program.strip(), payload.graduation_year.strip()))
        user_id = cur.lastrowid
        db.execute(
            "UPDATE invite_codes SET used_at=CURRENT_TIMESTAMP, used_by=? WHERE code_hash=? AND used_at IS NULL",
            (user_id, code_hash)
        )
    return {"access_token": create_token(user_id), "token_type": "bearer", "user": user_record(user_id)}

@app.post("/api/auth/login")
def login(payload: LoginPayload):
    with connect() as db:
        row = db.execute("SELECT id,password_hash FROM users WHERE email=?", (payload.email.lower().strip(),)).fetchone()
    if not row or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(401, "Email or password is incorrect.")
    return {"access_token": create_token(row["id"]), "token_type": "bearer", "user": user_record(row["id"])}

@app.get("/api/auth/me")
def auth_me(user_id: int = Depends(current_user)):
    return user_record(user_id)

@app.get("/api/profile")
def get_profile(user_id: int = Depends(current_user)):
    return user_record(user_id)

@app.put("/api/profile")
def update_profile(payload: ProfilePayload, user_id: int = Depends(current_user)):
    skills = list(dict.fromkeys(s.strip() for s in payload.skills if s.strip()))[:60]
    with connect() as db:
        db.execute("""UPDATE users SET full_name=?,university=?,program=?,graduation_year=?,
            location=?,work_authorization=?,skills=? WHERE id=?""",
            (payload.full_name.strip(), payload.university.strip(), payload.program.strip(),
             payload.graduation_year.strip(), payload.location.strip(),
             payload.work_authorization.strip(), json.dumps(skills), user_id))
    return user_record(user_id)

@app.post("/api/profile/resume")
async def upload_resume(file: UploadFile = File(...), user_id: int = Depends(current_user)):
    filename = Path(file.filename or "resume").name
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(400, "Resume must be PDF, DOCX, or TXT.")
    content = await file.read(MAX_RESUME_BYTES + 1)
    if len(content) > MAX_RESUME_BYTES:
        raise HTTPException(413, "Resume is too large. Maximum size is 5 MB.")
    if not content:
        raise HTTPException(400, "The uploaded file is empty.")
    try:
        extracted = extract_resume(filename, content).strip()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Could not read this resume. Try exporting it as PDF or TXT.")
    if not extracted:
        raise HTTPException(400, "No selectable text was found. Please upload a text-based PDF or DOCX.")
    folder = UPLOAD_DIR / str(user_id)
    folder.mkdir(parents=True, exist_ok=True)
    safe_name = f"{secrets.token_hex(12)}{suffix}"
    (folder / safe_name).write_bytes(content)
    with connect() as db:
        db.execute("UPDATE users SET resume_text=?,resume_filename=? WHERE id=?",
                   (extracted[:50000], filename[:200], user_id))
    return {"message": "Resume uploaded and text extracted.", "filename": filename, "characters": len(extracted)}

@app.post("/api/discover")
def discover(user_id: int = Depends(current_user)):
    return sync_job_sources()


@app.get("/api/discover/status")
def discover_status(user_id: int = Depends(current_user)):
    with connect() as db:
        rows = db.execute("""SELECT company,source,success,jobs_found,checked_at,error
            FROM source_syncs ORDER BY company COLLATE NOCASE,source""").fetchall()
        active_count = db.execute("SELECT COUNT(*) AS n FROM jobs WHERE is_active=1").fetchone()["n"]
    return {"configured_sources": len(source_inventory()), "checked_sources": len(rows),
            "healthy_sources": sum(1 for row in rows if row["success"]),
            "active_jobs": active_count, "sources": [dict(row) for row in rows]}

@app.get("/api/jobs")
def jobs(q: str = "", min_score: int = 0, user_id: int = Depends(current_user)):
    profile = full_profile(user_id)
    with connect() as db:
        rows = db.execute("""SELECT id,source,company,title,location,url,posted_at,employment_type,
            description,ai_match_score,match_explanation,matched_skills FROM jobs
            WHERE is_active=1 AND (title LIKE ? OR company LIKE ? OR location LIKE ?)
            ORDER BY posted_at DESC""", (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["match_score"] = score_job(item, profile)
        item.pop("description", None)
        if item["match_score"] >= min_score:
            result.append(item)
    result.sort(key=lambda x: (x["match_score"], x.get("posted_at") or ""), reverse=True)
    return result

@app.get("/api/jobs/{job_id}")
def job_detail(job_id: str, user_id: int = Depends(current_user)):
    with connect() as db:
        row = db.execute("SELECT id,source,company,title,location,url,description,posted_at,employment_type FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Job not found.")
    return dict(row)

@app.post("/api/jobs/{job_id}/ai-match")
def ai_match(job_id: str, user_id: int = Depends(current_user)):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(503, "AI matching is not configured. The site administrator must set OPENAI_API_KEY.")
    profile = full_profile(user_id)
    if not profile.get("resume_text") and not profile.get("skills"):
        raise HTTPException(400, "Add skills or upload your resume before using AI matching.")
    with connect() as db:
        job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not job:
        raise HTTPException(404, "Job not found.")
    from openai import OpenAI
    prompt = f"""Evaluate this student's fit for the job. Use only supplied facts. Never invent experience.
Return valid JSON with integer score from 0 to 100, concise explanation, matched_skills array,
missing_skills array, and suggested_actions array.
STUDENT PROFILE: {json.dumps({k: profile.get(k) for k in ['full_name','university','program','graduation_year','location','work_authorization','skills','resume_text']}, ensure_ascii=False)[:16000]}
JOB: {json.dumps({k: job[k] for k in ['title','company','location','description']}, ensure_ascii=False)[:12000]}"""
    try:
        response = OpenAI(api_key=key).chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role":"user","content":prompt}],
            response_format={"type":"json_object"}, temperature=0.2)
        data = json.loads(response.choices[0].message.content)
        score = max(0, min(100, int(data.get("score", 0))))
    except Exception as exc:
        raise HTTPException(502, f"AI matching failed: {str(exc)[:300]}")
    with connect() as db:
        db.execute("UPDATE jobs SET ai_match_score=?,match_explanation=?,matched_skills=? WHERE id=?",
                   (score, str(data.get("explanation", ""))[:2000],
                    json.dumps(data.get("matched_skills", [])[:30]), job_id))
    return {"score": score, "explanation": data.get("explanation", ""),
            "matched_skills": data.get("matched_skills", []),
            "missing_skills": data.get("missing_skills", []),
            "suggested_actions": data.get("suggested_actions", [])}

@app.post("/api/jobs/{job_id}/cover-letter")
def generate_cover_letter(job_id: str, user_id: int = Depends(current_user)):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(503, "Cover-letter drafting is not configured. The site administrator must set OPENAI_API_KEY.")
    profile = full_profile(user_id)
    if not profile.get("resume_text") and not profile.get("skills"):
        raise HTTPException(400, "Complete your profile or upload a resume before generating a cover letter.")
    with connect() as db:
        job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not job:
        raise HTTPException(404, "Job not found.")
    from openai import OpenAI
    prompt = f"""Write a concise, tailored cover letter for this role.
Use ONLY candidate facts below. Do not invent achievements, skills, projects, grades,
work authorization, or experience. Do not claim the student attends a different school.
Candidate: {json.dumps({k: profile.get(k) for k in ['full_name','university','program','graduation_year','location','work_authorization','skills','resume_text']}, ensure_ascii=False)[:16000]}
Job: {json.dumps({k: job[k] for k in ['title','company','location','description']}, ensure_ascii=False)[:12000]}
Return only the letter text."""
    try:
        result = OpenAI(api_key=key).chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role":"user","content":prompt}], temperature=0.4)
        letter = result.choices[0].message.content or ""
        if not letter.strip():
            raise ValueError("The model returned an empty draft.")
        return {"cover_letter": letter}
    except Exception as exc:
        raise HTTPException(502, f"Cover-letter generation failed: {str(exc)[:300]}")

@app.post("/api/applications")
def create_application(payload: ApplicationCreate, user_id: int = Depends(current_user)):
    with connect() as db:
        exists = db.execute("SELECT id FROM jobs WHERE id=?", (payload.job_id,)).fetchone()
        if not exists:
            raise HTTPException(404, "Job not found.")
        cur = db.execute("INSERT INTO applications(user_id,job_id,cover_letter,notes,status) VALUES(?,?,?,?,?)",
                         (user_id, payload.job_id, payload.cover_letter, payload.notes, "draft"))
    return {"id": cur.lastrowid, "status": "draft"}

@app.get("/api/applications")
def applications(user_id: int = Depends(current_user)):
    with connect() as db:
        rows = db.execute("""SELECT a.id,a.status,a.cover_letter,a.notes,a.created_at,
            j.company,j.title,j.url,j.location,j.id AS job_id
            FROM applications a JOIN jobs j ON j.id=a.job_id
            WHERE a.user_id=? ORDER BY a.created_at DESC""", (user_id,)).fetchall()
    return [dict(r) for r in rows]

@app.patch("/api/applications/{application_id}")
def update_application(application_id: int, payload: ApplicationUpdate, user_id: int = Depends(current_user)):
    allowed = {"draft", "ready_for_review", "submitted", "rejected", "withdrawn"}
    if payload.status not in allowed:
        raise HTTPException(400, "Unsupported application status.")
    with connect() as db:
        cur = db.execute("UPDATE applications SET status=? WHERE id=? AND user_id=?",
                         (payload.status, application_id, user_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Application not found.")
    return {"id": application_id, "status": payload.status}
