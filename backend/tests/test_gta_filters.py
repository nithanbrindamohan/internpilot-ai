"""GTA filtering/engineering discovery regressions; no live feeds or private DB."""
import os

os.environ.setdefault("TOKEN_SECRET", "unit-tests-only-local-secret-keep-private")
os.environ["ENABLE_JOB_SCHEDULER"] = "false"

from app.job_filters import enrich_job, matches_filters, region_for, term_for
from app.matching import is_relevant
from app.sources import BOARDS


def test_toronto_and_gta_not_the_same_as_canada_wide():
    assert region_for("Toronto, Ontario, Canada") == "gta"
    assert region_for("Mississauga, Ontario, Canada") == "gta"
    assert region_for("Vaughan, ON") == "gta"
    assert region_for("Waterloo, Ontario") == "waterloo"
    assert region_for("Canada - Remote") == "remote_canada"
    assert region_for("Vancouver, BC, Canada") == "canada_other"
    assert region_for("New York, NY") == "other"
    assert region_for("Unknown") != "gta"


def test_relevance_includes_non_software_engineering():
    for title in ("Mechanical Engineering Intern", "Civil Engineering Co-op",
                  "Electrical Engineering Student", "Mechatronics Intern"):
        assert is_relevant({"title":title,"location":"Mississauga, ON, Canada", "description":""}), title


def test_explicit_term_and_unknown():
    assert term_for("Software Engineering Intern (January 2027)")["start_term"] == "winter-2027"
    assert term_for("Mechanical Engineer - Summer 2027")["start_term"] == "summer-2027"
    assert term_for("Manufacturing Engineering Co-op")["start_term"] == ""
    assert term_for("Engineering Intern", "The program starts May 2027 and runs four months.")["start_term"] == "summer-2027"


def test_metadata_filters_and_safe_unknown_values():
    job = enrich_job({"title":"Mechanical Engineering Intern (Summer 2027)",
        "description":"Design CAD components", "location":"Markham, Ontario",
        "employment_type":"Intern/Co-op Hybrid"})
    assert job["discipline"] == "mechanical"
    assert job["work_mode"] == "hybrid"
    assert matches_filters(job, region="gta", discipline="mechanical", work_mode="hybrid", term="summer-2027")
    assert not matches_filters(job, region="canada_other")
    assert not matches_filters(job, term="winter-2027")
    unknown = enrich_job({"title":"Software Intern", "location":"Toronto", "description":""})
    assert unknown["start_label"] == "Not specified"
    assert not matches_filters(unknown, term="summer-2027")


def test_discovery_boards_include_gta_approved_candidates():
    keys = {b["key"] for b in BOARDS}
    assert "lever:kepler" in keys
    assert "ashby:human-computer-lab" in keys
    assert "ashby:trexo robotics" in keys


def test_jobs_endpoint_filters_with_separate_database(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from app import db, main
    from app.auth import create_token

    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'gta-filter-tests.db')
    db.init_db()
    with db.connect() as conn:
        conn.execute("INSERT INTO users(email,password_hash,full_name) VALUES ('student@example.test','x','Test')")
        for job_id, title, location, description, kind in (
            ('toronto-software', 'Software Engineering Intern (Winter 2027)', 'Toronto, Ontario', 'Developer co-op', 'Hybrid'),
            ('mississauga-mechanical', 'Mechanical Engineering Co-op (Summer 2027)', 'Mississauga, Ontario', 'Design CAD parts', 'On-site'),
            ('vancouver', 'Software Developer Intern', 'Vancouver, Canada', 'Co-op student', 'Remote'),
        ):
            conn.execute('''INSERT INTO jobs(id,company,title,location,url,description,employment_type,is_active)
                  VALUES(?,?,?,?,?,?,?,1)''', (job_id, 'Test Employer', title, location,
                  'https://example.org/'+job_id,description,kind))
    headers = {'Authorization': 'Bearer '+create_token(1)}
    with TestClient(main.app) as client:
        resp = client.get('/api/jobs?region=gta&discipline=mechanical&term=summer-2027', headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert [j['id'] for j in data] == ['mississauga-mechanical']
        assert data[0]['start_label'] == 'Summer 2027 (listed term)'
        assert 'match_explanation' not in data
        assert client.get('/api/jobs?region=invalid', headers=headers).status_code == 422
        assert client.get('/api/jobs?region=gta', headers=headers).status_code == 200
        assert [j['id'] for j in client.get('/api/jobs?region=gta&city=mississauga', headers=headers).json()] == ['mississauga-mechanical']
