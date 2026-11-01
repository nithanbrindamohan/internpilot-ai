import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "internpilot.db")))

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def _columns(db, table):
    return {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}

def init_db():
    with connect() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL DEFAULT '',
            university TEXT NOT NULL DEFAULT '',
            program TEXT NOT NULL DEFAULT '',
            graduation_year TEXT NOT NULL DEFAULT '',
            location TEXT NOT NULL DEFAULT 'Toronto, Ontario',
            work_authorization TEXT NOT NULL DEFAULT '',
            skills TEXT NOT NULL DEFAULT '[]',
            resume_text TEXT NOT NULL DEFAULT '',
            resume_filename TEXT NOT NULL DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""
        CREATE TABLE IF NOT EXISTS invite_codes (
            code_hash TEXT PRIMARY KEY,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            used_at TEXT,
            used_by INTEGER,
            note TEXT DEFAULT '',
            FOREIGN KEY(used_by) REFERENCES users(id) ON DELETE SET NULL
        )""")
        db.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, source TEXT, company TEXT, title TEXT,
            location TEXT, url TEXT, description TEXT, posted_at TEXT,
            employment_type TEXT, match_score INTEGER DEFAULT 0,
            ai_match_score INTEGER, match_explanation TEXT, matched_skills TEXT,
            source_key TEXT NOT NULL DEFAULT '', last_seen_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        )""")
        db.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            job_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            cover_letter TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        )""")
        # Safe, additive migrations for databases created by earlier MVP versions.
        if "ai_match_score" not in _columns(db, "jobs"):
            db.execute("ALTER TABLE jobs ADD COLUMN ai_match_score INTEGER")
        if "match_explanation" not in _columns(db, "jobs"):
            db.execute("ALTER TABLE jobs ADD COLUMN match_explanation TEXT")
        if "matched_skills" not in _columns(db, "jobs"):
            db.execute("ALTER TABLE jobs ADD COLUMN matched_skills TEXT")
        if "source_key" not in _columns(db, "jobs"):
            db.execute("ALTER TABLE jobs ADD COLUMN source_key TEXT NOT NULL DEFAULT ''")
        if "last_seen_at" not in _columns(db, "jobs"):
            db.execute("ALTER TABLE jobs ADD COLUMN last_seen_at TEXT")
        if "is_active" not in _columns(db, "jobs"):
            db.execute("ALTER TABLE jobs ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
        db.execute("""CREATE TABLE IF NOT EXISTS source_syncs (
            source_key TEXT PRIMARY KEY, company TEXT NOT NULL, source TEXT NOT NULL,
            success INTEGER NOT NULL DEFAULT 0, jobs_found INTEGER NOT NULL DEFAULT 0,
            checked_at TEXT NOT NULL, error TEXT NOT NULL DEFAULT ''
        )""")
        if "user_id" not in _columns(db, "applications"):
            db.execute("ALTER TABLE applications ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
        db.execute("CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(user_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs(is_active, posted_at)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source_key ON jobs(source_key)")
