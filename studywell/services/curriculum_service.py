from __future__ import annotations

import html
import re
import time
from typing import Any

import httpx

IB_DP_SUBJECTS = [
    "Studies in Language and Literature: Language A: Literature",
    "Studies in Language and Literature: Language A: Language and Literature",
    "Language Acquisition: Language B",
    "Language Acquisition: Ab initio",
    "Language Acquisition: Classical Languages (Latin/Greek)",
    "Individuals and Societies: Business Management",
    "Individuals and Societies: Digital Society",
    "Individuals and Societies: Economics",
    "Individuals and Societies: Geography",
    "Individuals and Societies: Global Politics",
    "Individuals and Societies: History",
    "Individuals and Societies: Philosophy",
    "Individuals and Societies: Psychology",
    "Individuals and Societies: Social and Cultural Anthropology",
    "Individuals and Societies: World Religions",
    "Sciences: Biology",
    "Sciences: Chemistry",
    "Sciences: Computer Science",
    "Sciences: Design Technology",
    "Sciences: Environmental Systems and Societies",
    "Sciences: Physics",
    "Sciences: Sports, Exercise and Health Science",
    "Mathematics: Analysis and Approaches",
    "Mathematics: Applications and Interpretation",
    "The Arts: Dance",
    "The Arts: Film",
    "The Arts: Music",
    "The Arts: Theatre",
    "The Arts: Visual Arts",
    "Interdisciplinary: Literature and Performance",
]

CAMBRIDGE_URLS = {
    "A Level": "https://www.cambridgeinternational.org/programmes-and-qualifications/cambridge-advanced/cambridge-international-as-and-a-levels/subjects/",
    "IGCSE": "https://www.cambridgeinternational.org/programmes-and-qualifications/cambridge-upper-secondary/cambridge-igcse/subjects/",
}

_SUBJECT_CACHE: dict[str, tuple[float, list[str]]] = {}
_CACHE_TTL_SECONDS = 60 * 60 * 24


def _extract_cambridge_subjects(page_html: str) -> list[str]:
    # Grab anchor labels that look like subject entries containing syllabus codes.
    anchor_texts = re.findall(r"<a[^>]+href=\"[^\"]+\"[^>]*>(.*?)</a>", page_html, flags=re.IGNORECASE | re.DOTALL)

    subjects: list[str] = []
    seen: set[str] = set()

    for raw in anchor_texts:
        txt = re.sub(r"<[^>]+>", "", raw)
        txt = html.unescape(txt).strip()
        txt = re.sub(r"\s+", " ", txt)

        if not txt:
            continue

        has_code = bool(re.search(r"\b\d{4}\b", txt))
        looks_like_subject = (
            " - " in txt
            or "(" in txt
            or "New" in txt
        )

        if not (has_code and looks_like_subject):
            continue

        if any(x in txt for x in ["Home", "Back to top", "Sitemap", "Cookie", "Privacy"]):
            continue

        if txt not in seen:
            seen.add(txt)
            subjects.append(txt)

    subjects.sort(key=lambda s: s.lower())
    return subjects


async def get_subjects_for_curriculum(curriculum: str) -> list[str]:
    c = curriculum.strip()
    if c == "IB":
        return IB_DP_SUBJECTS

    if c not in CAMBRIDGE_URLS:
        return []

    now = time.time()
    cached = _SUBJECT_CACHE.get(c)
    if cached and (now - cached[0] < _CACHE_TTL_SECONDS):
        return cached[1]

    url = CAMBRIDGE_URLS[c]
    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        subjects = _extract_cambridge_subjects(resp.text)

    _SUBJECT_CACHE[c] = (now, subjects)
    return subjects
