import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(tmp_path, monkeypatch):
    from app import db, main
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'test.db')
    monkeypatch.setenv('TOKEN_SECRET', 'test-token-secret-do-not-use-in-production-' * 3)
    monkeypatch.setenv('ENABLE_JOB_SCHEDULER','false')
    db.init_db()
    with db.connect() as con:
        con.execute("INSERT INTO users(email,password_hash,full_name,resume_text,resume_filename) VALUES(?,?,?,?,?)",
                    ('student@example.org','hash','Test Student','Private resume text','resume.pdf'))
        con.execute("INSERT INTO users(email,password_hash,full_name) VALUES(?,?,?)",('other@example.org','hash','Other Student'))
        con.execute("INSERT INTO jobs(id,company,title,location,url,description,is_active) VALUES(?,?,?,?,?,?,1)",
                    ('job1','ExampleCo','Engineering Intern','Markham','https://example.com/apply','Demo description'))
        con.execute("INSERT INTO applications(user_id,job_id,status) VALUES(1,'job1','draft')")
    monkeypatch.setattr(main, 'BackgroundScheduler', None)
    from app.auth import create_token
    with TestClient(main.app) as c:
        yield c, {'Authorization':f'Bearer {create_token(1)}'}, {'Authorization':f'Bearer {create_token(2)}'}

def test_packet_private_and_editable(client):
    c,auth,other=client
    r=c.get('/api/applications/1/packet',headers=other)
    assert r.status_code==404
    r=c.get('/api/applications/1/packet',headers=auth)
    assert r.status_code==200
    packet=r.json()
    assert packet['candidate']['email']=='student@example.org'
    assert 'resume_text' not in json.dumps(packet)
    assert packet['submission_confirmed'] is False
    r=c.put('/api/applications/1/content', headers=auth, json={'cover_letter':'Dear ExampleCo','answers':{'Phone':'555-0100'}})
    assert r.status_code==200
    fresh=c.get('/api/applications/1/packet',headers=auth).json()
    assert fresh['cover_letter']=='Dear ExampleCo'
    assert fresh['answers']['Phone']=='555-0100'
    assert c.put('/api/applications/1/content',headers=other,json={'cover_letter':'Hack','answers':{}}).status_code==404

def test_invalid_answer_rejected(client):
    c,auth,_=client
    assert c.put('/api/applications/1/content',headers=auth,json={'answers':{'Phone':'x'*3001}}).status_code==422
