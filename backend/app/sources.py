"""Public employer job-board integrations for InternPilot AI.

Only public postings are fetched. Applications always stay on the employer's
own application site. Board identifiers are checked independently at runtime;
a configured board is not considered healthy until its latest fetch succeeds.
"""
from __future__ import annotations

import hashlib
import html
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HEADERS = {
    "User-Agent": "InternPilotAI/1.0 (public internship and co-op discovery)",
    "Accept": "application/json, text/plain, */*",
}
TIMEOUT = (5, 18)
MAX_WORKERS = 8

# Public board identifiers. Greenhouse/Ashby/Lever are public posting feeds.
# Workday boards use the employer's public CXS search endpoint.
# A board can be temporarily empty or change its identifier; runtime health
# checks make that visible instead of silently treating it as connected.
BOARDS: list[dict[str, Any]] = []


def _add(kind: str, token: str, company: str, **extra: Any) -> None:
    BOARDS.append({"kind": kind, "token": token, "company": company,
                   "key": f"{kind}:{token}", **extra})


# Canadian technology companies and employers with Canadian career openings.
for token, company in [
    ("ada18", "Ada"), ("anthropic", "Anthropic"), ("coinbase", "Coinbase"),
    ("databricks", "Databricks"), ("d2l", "D2L"), ("faire", "Faire"),
    ("geotab", "Geotab"), ("gitlab", "GitLab"), ("hootsuite", "Hootsuite"),
    ("instacart", "Instacart"), ("lightmatter", "Lightmatter"), ("lyft", "Lyft"),
    ("mongodb", "MongoDB"), ("okta", "Okta"), ("pagerduty", "PagerDuty"),
    ("pinterest", "Pinterest"), ("reddit", "Reddit"), ("robinhood", "Robinhood"),
    ("samsara", "Samsara"), ("scaleai", "Scale AI"), ("shakepay", "Shakepay"),
    ("stackadapt", "StackAdapt"), ("stripe", "Stripe"), ("tailscale", "Tailscale"),
    ("tenstorrent", "Tenstorrent"), ("twilio", "Twilio"), ("affirm", "Affirm"),
    ("elastic", "Elastic"), ("dropbox", "Dropbox"), ("airbnb", "Airbnb"),
]:
    _add("greenhouse", token, company)

for token, company in [
    ("cohere", "Cohere"), ("wealthsimple", "Wealthsimple"),
    ("cerebras", "Cerebras"), ("kindred", "Kindred AI"),
    ("ideogram", "Ideogram"), ("miovision", "Miovision"), ("klue", "Klue"),
    ("thinkific", "Thinkific"), ("1password", "1Password"),
    ("loopio", "Loopio"), ("hopper", "Hopper"), ("clearco", "Clearco"),
    ("neofinancial", "Neo Financial"), ("jobber", "Jobber"), ("float", "Float"),
    ("ramp", "Ramp"), ("snowflake", "Snowflake"), ("confluent", "Confluent"),
    ("openai", "OpenAI"), ("telus-digital", "TELUS Digital"),
]:
    _add("ashby", token, company)

for token, company in [
    ("waabi", "Waabi"), ("benchsci", "BenchSci"),
    ("deepgenomics", "Deep Genomics"), ("pointclickcare", "PointClickCare"),
    ("wattpad", "Wattpad"), ("magnetforensics", "Magnet Forensics"),
    ("shyftlabs", "ShyftLabs"),
]:
    _add("lever", token, company)

# Workday public job-search endpoints (the public site remains the apply URL).
for company, endpoint, site_url in [
    ("Royal Bank of Canada", "https://rbc.wd3.myworkdayjobs.com/wday/cxs/rbc/RBCEARLYTALENT1/jobs", "https://rbc.wd3.myworkdayjobs.com/en-US/RBCEARLYTALENT1"),
    ("Royal Bank of Canada", "https://rbc.wd3.myworkdayjobs.com/wday/cxs/rbc/rbcglobal1/jobs", "https://rbc.wd3.myworkdayjobs.com/en-US/rbcglobal1"),
    ("TD", "https://td.wd3.myworkdayjobs.com/wday/cxs/td/TD_Bank_Careers/jobs", "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers"),
    ("CIBC", "https://cibc.wd3.myworkdayjobs.com/wday/cxs/cibc/search/jobs", "https://cibc.wd3.myworkdayjobs.com/en-US/search"),
    ("CIBC", "https://cibc.wd3.myworkdayjobs.com/wday/cxs/cibc/campus/jobs", "https://cibc.wd3.myworkdayjobs.com/en-US/campus"),
    ("BMO", "https://bmo.wd3.myworkdayjobs.com/wday/cxs/bmo/External/jobs", "https://bmo.wd3.myworkdayjobs.com/en-US/External"),
    ("Manulife", "https://manulife.wd3.myworkdayjobs.com/wday/cxs/manulife/MFCJH_Jobs/jobs", "https://manulife.wd3.myworkdayjobs.com/en-US/MFCJH_Jobs"),
    ("Sun Life", "https://sunlife.wd3.myworkdayjobs.com/wday/cxs/sunlife/Experienced-Jobs/jobs", "https://sunlife.wd3.myworkdayjobs.com/en-US/Experienced-Jobs"),
    ("NVIDIA", "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs", "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"),
    ("Intel", "https://intel.wd1.myworkdayjobs.com/wday/cxs/intel/External/jobs", "https://intel.wd1.myworkdayjobs.com/en-US/External"),
    ("Autodesk", "https://autodesk.wd1.myworkdayjobs.com/wday/cxs/autodesk/Ext/jobs", "https://autodesk.wd1.myworkdayjobs.com/en-US/Ext"),
    ("Ciena", "https://ciena.wd5.myworkdayjobs.com/wday/cxs/ciena/Careers/jobs", "https://ciena.wd5.myworkdayjobs.com/en-US/Careers"),
    ("Thomson Reuters", "https://thomsonreuters.wd5.myworkdayjobs.com/wday/cxs/thomsonreuters/External_Career_Site/jobs", "https://thomsonreuters.wd5.myworkdayjobs.com/en-US/External_Career_Site"),
    ("Magna", "https://magna.wd3.myworkdayjobs.com/wday/cxs/magna/Magna/jobs", "https://magna.wd3.myworkdayjobs.com/en-US/Magna"),
]:
    _add("workday", endpoint, company, site_url=site_url)


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=2, connect=2, read=2, status=2, backoff_factor=0.35,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=frozenset(["GET", "POST"]))
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    return session


def _plain(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _job_id(company: str, url: str) -> str:
    canonical = (url or "").strip().split("#", 1)[0]
    return hashlib.sha256(f"{company.casefold()}|{canonical}".encode("utf-8")).hexdigest()[:24]


def _date(value: Any, milliseconds: bool = False) -> str:
    if value in (None, ""):
        return ""
    try:
        if isinstance(value, (int, float)):
            seconds = float(value) / (1000 if milliseconds or value > 10_000_000_000 else 1)
            return datetime.fromtimestamp(seconds, timezone.utc).isoformat()
        raw = str(value).strip()
        relative = re.fullmatch(r"(?:posted\s+)?(today|yesterday|\d+\s+days?\s+ago|\d+\s+weeks?\s+ago)", raw, re.I)
        if relative:
            phrase = relative.group(1).lower()
            days = 0 if phrase == "today" else 1 if phrase == "yesterday" else int(phrase.split()[0]) * (7 if "week" in phrase else 1)
            return (datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
                    - timedelta(days=days)).isoformat()
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat()
        except ValueError:
            return parsedate_to_datetime(raw).astimezone(timezone.utc).isoformat()
    except Exception:
        return str(value)[:80]


def _base(source: dict, title: str, location: str, url: str, description: str,
          posted_at: Any = "", employment_type: str = "") -> dict | None:
    if not title or not url or not str(url).startswith("https://"):
        return None
    return {
        "id": _job_id(source["company"], str(url)),
        "source_key": source["key"],
        "source": source["kind"].title(),
        "company": source["company"],
        "title": _plain(title)[:300],
        "location": _plain(location)[:300],
        "url": str(url),
        "description": _plain(description)[:30000],
        "posted_at": _date(posted_at, milliseconds=source["kind"] == "lever"),
        "employment_type": _plain(employment_type)[:100],
    }


def fetch_greenhouse(source: dict) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{source['token']}/jobs?content=true"
    response = _session().get(url, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    jobs = []
    for item in data.get("jobs", []):
        job = _base(source, item.get("title"), (item.get("location") or {}).get("name"),
                    item.get("absolute_url"), item.get("content"), item.get("updated_at"))
        if job:
            jobs.append(job)
    return jobs


def fetch_lever(source: dict) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{source['token']}?mode=json"
    response = _session().get(url, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    jobs = []
    for item in data if isinstance(data, list) else []:
        cats = item.get("categories") or {}
        job = _base(source, item.get("text"), cats.get("location"), item.get("hostedUrl"),
                    item.get("descriptionPlain") or item.get("description"), item.get("createdAt"),
                    cats.get("commitment") or item.get("workplaceType", ""))
        if job:
            jobs.append(job)
    return jobs


def fetch_ashby(source: dict) -> list[dict]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{source['token']}"
    response = _session().get(url, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    jobs = []
    for item in data.get("jobs", []):
        if item.get("isListed") is False:
            continue
        locations = [item.get("location", "")]
        locations.extend(x.get("location", "") for x in item.get("secondaryLocations", []) if isinstance(x, dict))
        location = ", ".join(dict.fromkeys(x for x in locations if x))
        job = _base(source, item.get("title"), location,
                    item.get("jobUrl") or item.get("applyUrl"),
                    item.get("descriptionPlain") or item.get("descriptionHtml"),
                    item.get("publishedAt"), item.get("employmentType") or item.get("workplaceType", ""))
        if job:
            jobs.append(job)
    return jobs


def fetch_workday(source: dict) -> list[dict]:
    endpoint = source["token"]
    site_url = source["site_url"].rstrip("/")
    session = _session()
    all_jobs: list[dict] = []
    offset, limit = 0, 20
    for _ in range(10):
        response = session.post(endpoint,
            json={"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""},
            headers={"Content-Type": "application/json", "Accept": "application/json"}, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        items = data.get("jobPostings") or data.get("jobs") or []
        if not isinstance(items, list) or not items:
            break
        for item in items:
            external_path = item.get("externalPath") or item.get("externalUrl") or ""
            if external_path.startswith("http"):
                job_url = external_path
            elif external_path:
                job_url = site_url + (external_path if external_path.startswith("/") else "/" + external_path)
            else:
                continue
            job = _base(source, item.get("title"), item.get("locationsText") or item.get("location"),
                        job_url, item.get("description") or " ".join(item.get("bulletFields") or []),
                        item.get("postedOn") or item.get("postedDate"), item.get("employmentType", ""))
            if job:
                all_jobs.append(job)
        total = data.get("total")
        offset += len(items)
        if len(items) < limit or (isinstance(total, int) and offset >= total):
            break
    return all_jobs

FETCHERS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever,
            "ashby": fetch_ashby, "workday": fetch_workday}


def _fetch_one(source: dict) -> tuple[list[dict], dict]:
    checked_at = datetime.now(timezone.utc).isoformat()
    try:
        jobs = FETCHERS[source["kind"]](source)
        return jobs, {"source_key": source["key"], "company": source["company"],
                      "source": source["kind"].title(), "success": True,
                      "jobs_found": len(jobs), "checked_at": checked_at, "error": ""}
    except Exception as exc:
        message = f"{type(exc).__name__}: {str(exc)[:220]}"
        return [], {"source_key": source["key"], "company": source["company"],
                    "source": source["kind"].title(), "success": False,
                    "jobs_found": 0, "checked_at": checked_at, "error": message}


def discover_jobs() -> tuple[list[dict], list[str], list[dict]]:
    """Fetch all configured public boards concurrently with per-board isolation."""
    results: list[dict] = []
    statuses: list[dict] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(_fetch_one, source) for source in BOARDS]
        for future in as_completed(futures):
            jobs, status = future.result()
            results.extend(jobs)
            statuses.append(status)
    statuses.sort(key=lambda x: (x["company"].casefold(), x["source_key"]))
    # A URL can appear on more than one feed; keep one record per employer URL.
    deduped: dict[str, dict] = {}
    for job in results:
        deduped[job["id"]] = job
    errors = [f"{s['company']} ({s['source']}): {s['error']}" for s in statuses if not s["success"]]
    return list(deduped.values()), errors, statuses


def source_inventory() -> list[dict]:
    return [{"company": b["company"], "source": b["kind"].title(), "source_key": b["key"]}
            for b in BOARDS]
