import unittest
from unittest.mock import patch

from app import sources


class FakeResponse:
    def __init__(self, data):
        self.data = data
    def raise_for_status(self):
        return None
    def json(self):
        return self.data


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []
    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.response
    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.response


class SourceAdapterTests(unittest.TestCase):
    def test_greenhouse_normalizes_public_job(self):
        fake = FakeSession(FakeResponse({"jobs": [{
            "title": "Software Developer Intern", "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
            "location": {"name": "Toronto, ON"}, "content": "<p>Python and Java</p>",
            "updated_at": "2026-10-30T10:00:00Z"
        }]}))
        with patch.object(sources, "_session", return_value=fake):
            jobs = sources.fetch_greenhouse({"kind": "greenhouse", "token": "acme", "company": "Acme", "key": "greenhouse:acme"})
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["location"], "Toronto, ON")
        self.assertIn("Python", jobs[0]["description"])
        self.assertEqual(jobs[0]["source_key"], "greenhouse:acme")

    def test_lever_created_timestamp_is_normalized(self):
        fake = FakeSession(FakeResponse([{
            "text": "QA Co-op", "hostedUrl": "https://jobs.lever.co/acme/abc",
            "categories": {"location": "Ontario, Canada", "commitment": "Internship"},
            "descriptionPlain": "Test automation", "createdAt": 1793354400000
        }]))
        with patch.object(sources, "_session", return_value=fake):
            jobs = sources.fetch_lever({"kind": "lever", "token": "acme", "company": "Acme", "key": "lever:acme"})
        self.assertEqual(jobs[0]["employment_type"], "Internship")
        self.assertTrue(jobs[0]["posted_at"].endswith("+00:00"))

    def test_ashby_skips_unlisted_jobs(self):
        fake = FakeSession(FakeResponse({"jobs": [
            {"title": "Listed Intern", "isListed": True, "location": "Toronto, Canada",
             "jobUrl": "https://jobs.ashbyhq.com/acme/1", "descriptionPlain": "Software internship"},
            {"title": "Unlisted Intern", "isListed": False, "location": "Toronto, Canada",
             "jobUrl": "https://jobs.ashbyhq.com/acme/2"}
        ]}))
        with patch.object(sources, "_session", return_value=fake):
            jobs = sources.fetch_ashby({"kind": "ashby", "token": "acme", "company": "Acme", "key": "ashby:acme"})
        self.assertEqual([j["title"] for j in jobs], ["Listed Intern"])

    def test_workday_paginates_and_builds_apply_link(self):
        fake = FakeSession(FakeResponse({"total": 1, "jobPostings": [{
            "title": "Developer Co-op", "locationsText": "Toronto, Ontario",
            "externalPath": "/job/Toronto-ON/Developer-Co-op_R123", "postedOn": "Posted Today"
        }]}))
        with patch.object(sources, "_session", return_value=fake):
            jobs = sources.fetch_workday({"kind": "workday", "token": "https://tenant.wd3.myworkdayjobs.com/wday/cxs/t/site/jobs",
                                         "company": "Example", "key": "workday:site",
                                         "site_url": "https://tenant.wd3.myworkdayjobs.com/en-US/site"})
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["url"], "https://tenant.wd3.myworkdayjobs.com/en-US/site/job/Toronto-ON/Developer-Co-op_R123")
        self.assertTrue(jobs[0]["posted_at"].startswith("2026-10-31T12:00:00"))

    def test_job_ids_are_stable_for_same_company_and_url(self):
        url = "https://jobs.example.com/role/123?source=feed"
        self.assertEqual(sources._job_id("Example", url), sources._job_id("EXAMPLE", url))


if __name__ == "__main__":
    unittest.main()
