import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import db, main


class SyncBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_path = db.DB_PATH
        db.DB_PATH = Path(self.temp.name) / "test.db"
        db.init_db()
        self.job = {
            "id": "stable-job-id", "source_key": "greenhouse:example", "source": "Greenhouse",
            "company": "Example", "title": "Software Developer Intern",
            "location": "Toronto, Ontario, Canada", "url": "https://boards.greenhouse.io/example/jobs/1",
            "description": "Python internship student role", "posted_at": "2026-10-30T00:00:00+00:00",
            "employment_type": ""
        }
        self.status = {"source_key": "greenhouse:example", "company": "Example", "source": "Greenhouse",
                       "success": True, "jobs_found": 1, "checked_at": "2026-10-31T00:00:00+00:00", "error": ""}

    def tearDown(self):
        db.DB_PATH = self.original_path
        self.temp.cleanup()

    def active_count(self):
        with db.connect() as conn:
            return conn.execute("SELECT COUNT(*) AS n FROM jobs WHERE is_active=1").fetchone()["n"]

    def test_source_failure_does_not_delete_old_jobs_but_successful_empty_feed_does(self):
        with patch.object(main, "discover_jobs", return_value=([self.job], [], [self.status])):
            main.sync_job_sources()
        self.assertEqual(self.active_count(), 1)

        failed = {**self.status, "success": False, "jobs_found": 0, "error": "temporary timeout"}
        with patch.object(main, "discover_jobs", return_value=([], ["Example timeout"], [failed])):
            main.sync_job_sources()
        self.assertEqual(self.active_count(), 1)

        empty_success = {**self.status, "jobs_found": 0}
        with patch.object(main, "discover_jobs", return_value=([], [], [empty_success])):
            main.sync_job_sources()
        self.assertEqual(self.active_count(), 0)


if __name__ == "__main__":
    unittest.main()
