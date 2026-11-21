import json
import re

ROLE_TERMS = [
    "software", "developer", "programmer", "quality engineer", "qa engineer",
    "sdet", "test automation", "machine learning", "artificial intelligence",
    "data engineer", "full stack", "frontend", "front-end", "backend", "back-end",
    "cloud engineer", "devops", "cybersecurity",
    "mechanical", "electrical", "electronics", "civil engineering", "structural",
    "mechatronics", "robotics", "controls engineer", "manufacturing engineer",
    "process engineer", "chemical engineer", "aerospace", "hardware engineer",
    "embedded", "fpga", "engineering intern", "engineering co-op", "engineering student"
]
STUDENT_TERMS = ["intern", "internship", "co-op", "coop", "student", "new grad", "early career", "summer student", "work term"]
SENIOR_TERMS = ["senior", "staff engineer", "principal", "director", "vice president"]

def _skills(profile):
    value = profile.get("skills", [])
    if isinstance(value, str):
        try: value = json.loads(value)
        except Exception: value = [x.strip() for x in value.split(",")]
    return [str(x).strip() for x in value if str(x).strip()]

def score_job(job, profile):
    title = (job.get("title") or "").lower()
    text = (title + " " + (job.get("description") or "")).lower()
    location = (job.get("location") or "").lower()
    score = 0
    if any(term in title for term in ROLE_TERMS): score += 30
    elif any(term in text for term in ROLE_TERMS): score += 18
    if any(term in text for term in STUDENT_TERMS): score += 25
    if any(x in location for x in ["toronto", "ontario", "vaughan", "waterloo", "ottawa", "mississauga", "markham", "brampton", "richmond hill", "oakville", "oshawa", "pickering", "canada"]):
        score += 25
    elif "remote" in location: score += 20
    skill_hits = sum(1 for skill in _skills(profile) if skill.lower() in text)
    score += min(20, skill_hits * 4)
    if any(term in title for term in SENIOR_TERMS): score -= 35
    return max(0, min(100, score))

def is_relevant(job):
    title = (job.get("title") or "").lower()
    text = title + " " + (job.get("description") or "").lower()
    location = (job.get("location") or "").lower()
    role = any(term in text for term in ROLE_TERMS)
    region = any(x in location for x in ["ontario", "toronto", "vaughan", "waterloo", "ottawa", "mississauga", "markham", "brampton", "richmond hill", "oakville", "oshawa", "pickering", "canada", "remote"])
    student = any(term in text for term in STUDENT_TERMS)
    return role and region and student
