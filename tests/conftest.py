"""All integration tests use isolated temporary storage. No live APIs are called."""
import hashlib
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
os.environ['TOKEN_SECRET'] = 'isolated-test-secret-for-internpilot-never-use-in-production'
os.environ['ENABLE_JOB_SCHEDULER'] = 'false'
os.environ['OPENAI_API_KEY'] = 'fake-test-key-no-api-calls'

from app import db, main, auth

@pytest.fixture
def test_env(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'isolated-tests.db')
    monkeypatch.setattr(main, 'UPLOAD_DIR', tmp_path / 'uploads')
    monkeypatch.setattr(main, 'discover_jobs', lambda: ([], [], []))
    monkeypatch.setattr(auth, 'TOKEN_SECRET', 'isolated-test-secret-for-internpilot-never-use-in-production')
    db.init_db()
    with TestClient(main.app) as client:
        yield client, db

@pytest.fixture
def invite(test_env):
    _client, db = test_env
    value = 'IP-ABCD-1234-5678'
    normalized = value.upper().replace('-', '').replace(' ', '')
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    with db.connect() as conn:
        conn.execute('INSERT INTO invite_codes(code_hash) VALUES(?)', (digest,))
    return value

@pytest.fixture
def register(test_env):
    client, db = test_env
    counter = [0]
    def create(name='Alice', code=None):
        counter[0] += 1
        code = code or f'IP-TST{counter[0]:04d}-ABCDEF'
        normalized = code.upper().replace('-', '').replace(' ', '')
        digest = hashlib.sha256(normalized.encode()).hexdigest()
        with db.connect() as conn:
            conn.execute('INSERT INTO invite_codes(code_hash) VALUES(?)', (digest,))
        email = f'test{counter[0]}@example.com'
        payload = {'full_name': name, 'email': email, 'password': 'SafeTestPass123!', 'invite_code': code, 'program': 'Software Engineering'}
        response = client.post('/api/auth/register', json=payload)
        assert response.status_code == 200, response.text
        return {'email': email, 'token': response.json()['access_token'], 'headers': {'Authorization': 'Bearer '+response.json()['access_token']}, 'user': response.json()['user']}
    return create

@pytest.fixture
def job(test_env):
    client, db = test_env
    with db.connect() as conn:
        conn.execute('''INSERT INTO jobs(id,source,company,title,location,url,description,employment_type,source_key,is_active)
           VALUES (?,?,?,?,?,?,?,?,?,1)''',
           ('job-1','Greenhouse','Example Company','Software Engineering Intern','Toronto, Ontario','https://example.com/jobs/1','Python React SQL internship','Internship','greenhouse:example'))
    return 'job-1'
