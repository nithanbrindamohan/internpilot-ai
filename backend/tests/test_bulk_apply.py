"""Isolated bulk-application tests. Never uses the real database or sends applications."""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("TOKEN_SECRET", "bulk-apply-unit-testing-secret-only-do-not-deploy")
os.environ["ENABLE_JOB_SCHEDULER"] = "false"

from fastapi.testclient import TestClient
from app import db, main
from app.auth import create_token


def test_bulk_workflow_isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "isolated-test.db")
    db.init_db()
    with db.connect() as conn:
        conn.execute("INSERT INTO users(email,password_hash,full_name) VALUES ('a@example.test','x','A')")
        conn.execute("INSERT INTO users(email,password_hash,full_name) VALUES ('b@example.test','x','B')")
        for i in range(1, 4):
            conn.execute("""INSERT INTO jobs(id,company,title,url,is_active)
                VALUES(?,?,?,?,1)""", (f"job-{i}", "Example Company", "Student Intern",
                    f"https://example.org/jobs/{i}"))
    user_a = {"Authorization": "Bearer " + create_token(1)}
    user_b = {"Authorization": "Bearer " + create_token(2)}
    with TestClient(main.app) as client:
        response = client.post("/api/applications/bulk", headers=user_a, json={"job_ids": ["job-1", "job-2", "job-1"]})
        assert response.status_code == 200, response.text
        created = response.json()["created"]
        assert len(created) == 2
        assert response.json()["message"].endswith("No applications were submitted.")
        assert client.post("/api/applications/bulk", headers=user_a, json={"job_ids": ["job-1"]}).json()["already_saved"]
        assert client.post("/api/applications/bulk/handoff", headers=user_a, json={
            "application_ids": [created[0]["application_id"]], "confirm_reviewed": False}).status_code == 400
        assert client.post("/api/applications/bulk/handoff", headers=user_b, json={
            "application_ids": [created[0]["application_id"]], "confirm_reviewed": True}).status_code == 404
        response = client.post("/api/applications/bulk/handoff", headers=user_a, json={
            "application_ids": [x["application_id"] for x in created], "confirm_reviewed": True})
        assert response.status_code == 200, response.text
        assert all(x["submission_confirmed"] is False for x in response.json()["applications"])
        apps = client.get("/api/applications", headers=user_a).json()
        assert len(apps) == 2
        assert all(a["status"] == "ready_for_review" for a in apps)
        assert all(a["submission_state"] == "needs_manual_submission" for a in apps)
        assert client.get("/api/applications", headers=user_b).json() == []
        # A manually selected status is clearly labeled as user reported, not provider confirmed.
        patch = client.patch(f'/api/applications/{created[0]["application_id"]}', headers=user_a,
                             json={"status": "submitted"})
        assert patch.status_code == 200
        changed = client.get("/api/applications", headers=user_a).json()
        assert next(a for a in changed if a["id"] == created[0]["application_id"])["submission_state"] == "user_reported_submitted"
        assert client.post("/api/applications/bulk/handoff", headers=user_a, json={
            "application_ids": [created[0]["application_id"]], "confirm_reviewed": True}).status_code == 409


def test_bulk_disallows_missing_auth_and_over_limit(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "another-test.db")
    db.init_db()
    with TestClient(main.app) as client:
        assert client.post("/api/applications/bulk", json={"job_ids": ["job-1"]}).status_code == 401
        assert client.post("/api/applications/bulk", json={"job_ids": [str(n) for n in range(11)]}).status_code in {401,422}
