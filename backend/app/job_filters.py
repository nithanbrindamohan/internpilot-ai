"""Deterministic metadata for filtering public internship postings.

Term values are hints parsed from explicit posting language, not guaranteed
start dates. GTA matching never treats a generic 'Canada' label as Toronto.
"""
from __future__ import annotations

import re

GTA_CITIES = (
    'toronto', 'north york', 'scarborough', 'etobicoke', 'york',
    'vaughan', 'richmond hill', 'markham', 'newmarket', 'aurora',
    'mississauga', 'brampton', 'caledon', 'oakville', 'burlington',
    'milton', 'halton hills', 'ajax', 'pickering', 'whitby', 'oshawa',
    'clarington', 'east gwillimbury', 'king city', 'stouffville',
)
DISCIPLINES = {
    'software': ('software', 'developer', 'frontend', 'front-end', 'backend', 'back-end',
                 'full stack', 'full-stack', 'devops', 'cloud engineer', 'sdet', 'qa engineer', 'cybersecurity'),
    'mechanical': ('mechanical', 'manufacturing', 'automotive', 'cad ', 'thermal', 'hvac'),
    'electrical': ('electrical', 'electronics', 'fpga', 'power systems', 'embedded', 'hardware', 'pcb'),
    'civil': ('civil', 'structural', 'transportation', 'geotechnical', 'construction', 'municipal'),
    'mechatronics': ('mechatronic', 'robotics', 'controls engineer', 'automation engineer'),
    'data_ai': ('machine learning', 'ml engineer', 'ai engineer', 'data engineer',
                'artificial intelligence', 'data scientist'),
    'chemical': ('chemical engineer', 'process engineer', 'materials engineer'),
    'aerospace': ('aerospace', 'aeronautical', 'satellite', 'avionics'),
}
SEASONS = {'winter': ('winter', 'jan', 'january', 'feb', 'february'),
           'spring': ('spring', 'mar', 'march', 'apr', 'april'),
           'summer': ('summer', 'may', 'jun', 'june', 'jul', 'july', 'aug', 'august'),
           'fall': ('fall', 'autumn', 'sep', 'sept', 'september', 'oct', 'october', 'nov', 'november')}
# Anchored to an explicit start/term context or a term in the title.
TERM_RE = re.compile(r'\b(winter|spring|summer|fall|autumn|january|february|march|april|may|june|july|august|september|october|november)\s*[,/\- ]*\s*(20\d{2})\b', re.I)
EXPLICIT_CONTEXT = re.compile(r'\b(start(?:ing)?|starts?|begin(?:ning|s)?|term|intake|co-op|internship)\b', re.I)


def _normalized(text):
    return re.sub(r'\s+', ' ', str(text or '').lower())


def region_for(location):
    loc = _normalized(location)
    if not loc:
        return 'unknown'
    # Prevent matching "York" within "New York".
    if any(re.search(r'(?<![a-z])' + re.escape(city) + r'(?![a-z])', loc)
           for city in GTA_CITIES if city != 'york') or re.search(r'\bgreater toronto area\b|\bgta\b', loc):
        return 'gta'
    if re.search(r'(?<!new )\byork(?: region)?\b', loc) and ('ontario' in loc or 'canada' in loc):
        return 'gta'
    if any(x in loc for x in ('waterloo', 'kitchener', 'cambridge, on', 'guelph')):
        return 'waterloo'
    if 'ontario' in loc or re.search(r'\bottawa\b|\blondon, on\b|\bhamilton\b', loc):
        return 'ontario_other'
    if 'remote' in loc and ('canada' in loc or 'ontario' in loc):
        return 'remote_canada'
    if 'canada' in loc or re.search(r'\b(?:bc|alberta|quebec|montreal|vancouver)\b', loc):
        return 'canada_other'
    return 'other'


def discipline_for(title, description=''):
    title = _normalized(title)
    description = _normalized(description)
    hits = [name for name, phrases in DISCIPLINES.items() if any(p in title for p in phrases)]
    if hits:
        return hits[0]
    if 'engineering' in title or 'engineer' in title:
        return 'general'
    # Titles sometimes only say "Intern, R&D"; use description as fallback.
    for name, phrases in DISCIPLINES.items():
        if any(p in description[:1800] for p in phrases):
            return name
    return 'other'


def work_mode_for(job):
    text = _normalized(' '.join(str(job.get(k) or '') for k in ('location', 'employment_type')))
    if 'hybrid' in text:
        return 'hybrid'
    if 'remote' in text:
        return 'remote'
    if 'on-site' in text or 'onsite' in text or 'in-person' in text:
        return 'onsite'
    return 'unspecified'


def term_for(title, description=''):
    # Search titles first. Description requires explicit start/term context nearby.
    title = _normalized(title)
    description = _normalized(description)
    match = TERM_RE.search(title)
    if not match:
        for candidate in TERM_RE.finditer(description[:7000]):
            context = description[max(0, candidate.start()-90):candidate.end()+45]
            if EXPLICIT_CONTEXT.search(context):
                match = candidate
                break
    if not match:
        return {'start_term': '', 'start_label': 'Not specified'}
    month_or_season, year = match.group(1).lower(), match.group(2)
    if month_or_season == 'autumn':
        month_or_season = 'fall'
    season = next((s for s, words in SEASONS.items() if any(month_or_season == w for w in words)), '')
    if not season:
        return {'start_term': '', 'start_label': 'Not specified'}
    return {'start_term': f'{season}-{year}', 'start_label': f'{season.title()} {year} (listed term)'}


def enrich_job(job):
    item = dict(job)
    item['region'] = region_for(item.get('location'))
    item['discipline'] = discipline_for(item.get('title'), item.get('description'))
    item['work_mode'] = work_mode_for(item)
    item.update(term_for(item.get('title'), item.get('description')))
    return item


def matches_filters(job, region='all', discipline='all', work_mode='all', term='all'):
    if region != 'all' and job['region'] != region:
        return False
    if discipline != 'all' and job['discipline'] != discipline:
        return False
    if work_mode != 'all' and job['work_mode'] != work_mode:
        return False
    if term != 'all' and job['start_term'] != term:
        return False
    return True
