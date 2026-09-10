# ------------ imports --------------------
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import json
from anthropic import Anthropic
from urllib.parse import urlsplit, urlunsplit

# ------------ setup ------------------------
load_dotenv()

from sources import newgrad2027
from sources import speedyapply
from db_tools import get_client
from fetch_job_text import JobTextFetcher

# --------------- relevance score via claude ----------------
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MAX_DESCRIPTION_CHARS = 3000  # keep token cost bounded

# Same set used in check_extraction.py — kept identical so "closed" means the
# same thing everywhere in the pipeline, not a slightly different heuristic
# per script.
CLOSED_POSTING_PATTERNS = [
    "no longer accepting applications",
    "this position has been filled",
    "posting has expired",
    "job is no longer available",
    "position is closed",
]


def posting_status(status_code, text):
    """'dead' (fetch failed / no usable text), 'closed' (fetched fine, but
    the page itself says the posting is closed), or 'open'. Dead and closed
    postings should never reach classify_job or the database."""
    if status_code is None or not text:
        return "dead"
    lowered = text.lower()
    if any(pattern in lowered for pattern in CLOSED_POSTING_PATTERNS):
        return "closed"
    return "open"


def build_description_block(text):
    if not text:
        return ""
    snippet = text[:MAX_DESCRIPTION_CHARS]
    return f"\nJob description excerpt:\n{snippet}\n"


CLASSIFICATION_PROMPT = """You are helping a computer science student graduating May 2027 evaluate new-grad job postings for Forward Deployed Engineer (FDE) or Software Engineer (SWE) roles.

Given this posting:
Company: {company}
Title: {title}
Location: {location}
{description_block}

The candidate's preferences:
- Location, in order of preference: (1) Chicago, (2) Chicagoland Area, (3) Big Cities in the Midwest, (4) Portland/Washington, (5) anywhere in the USA as a lower-priority fallback
- No preference on company type/size (big tech, startup, and quant/finance are all fine)
- Strongly prefer roles that use Python, involve building/working with AI agents, or otherwise involve hands-on AI/LLM usage — score higher when the title or description clearly indicates this

Graduation-year matching (read from the title or description text — don't assume if it isn't stated):
- If the posting is explicitly labeled "New Grad 2027" (or equivalent, e.g. "Class of 2027"), or the description states a graduation window overlapping December 2026 through June 2027 (e.g. "on track to graduate between December 2026 and June 2027"), treat this as a strong positive signal
- If the posting is explicitly labeled "New Grad 2026" (or equivalent, e.g. "Class of 2026"), set relevant: false and score: 1 — wrong class year, not a fit regardless of anything else about the role
- If no graduation year is stated anywhere in the posting, don't penalize it for that absence — evaluate on the other criteria alone

Respond with ONLY a JSON object, no other text, in this exact format:
{{"relevant": true or false, "score": 1-10, "reason": "one short sentence"}}

Scoring guidance:
- Set relevant: false and score: 1 for an explicit "New Grad 2026" label, regardless of how good the role otherwise looks
- For everything else, score higher for roles that closely match FDE or general SWE work AND match a higher-priority location tier AND match the Python/AI-agent/AI-usage or 2027-grad-year signals above
- A strong SWE/FDE role in a lower-priority location should still score reasonably (5-7), not be penalized as heavily as a wrong-class-year mismatch
- Score lower (5-7) but still relevant: true for adjacent roles or acceptable-but-not-ideal locations
- Only use relevant: false for an explicit "New Grad 2026" label or roles that clearly aren't software engineering work despite matching our keyword filter"""

BLOCKED_COMPANIES = {
    "palantir",
    "flock safety",
    "at&t",
    "deloitte",
    "motorola solutions",
    "l3 harris",
    "fedex",
    "comcast",
    "charter communications",
    "clearview ai",
    "axon",
    "geolitica",
    "lexisnexis",
    "dji",
    "digital receiver technology",
    "fog data science",
}

DEALBREAKER_KEYWORDS = [
    "raytheon", "boeing", "northrop grumman", "lockheed",
    "gdit", "leidos", "caci", "booz allen",
]

def is_blocked_company(company_name):
    lowered = company_name.strip().lower()
    if lowered in BLOCKED_COMPANIES:
        return True
    return any(keyword in lowered for keyword in DEALBREAKER_KEYWORDS)

def classify_job(job, description=None):
    prompt = CLASSIFICATION_PROMPT.format(
        company=job["company"],
        title=job["title"],
        location=job["location"],
        description_block=build_description_block(description),
    )
    fallback = {"relevant": True, "score": 5, "reason": "classification failed, defaulted"}

    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.content[0].text.strip()
        raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(raw_text)

        # guard against valid-JSON-but-wrong-shape responses
        if not isinstance(result, dict) or "score" not in result:
            print(f"  Unexpected classification shape for {job['company']}: {raw_text}")
            return fallback

        return result
    
    except Exception as e:
        # catches JSON errors AND API-level issues
        print(f"  Classification error for {job['company']}: {e}")
        return fallback

# ----------------- add to tracker -------------------------
def canonicalize_link(url):
    if not url:
        return url
    parts = urlsplit(url)
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))

def get_existing_ids(client):
    ids = set()
    canonical_links = set()
    page_size = 1000
    offset = 0
    while True:
        batch = client.table("job_postings").select("id, link").range(offset, offset + page_size - 1).execute().data
        for row in batch:
            ids.add(row["id"])
            if row.get("link"):
                canonical_links.add(canonicalize_link(row["link"]))
        if len(batch) < page_size:
            break
        offset += page_size
    return ids, canonical_links

def add_new_jobs(client, jobs, existing_ids, existing_canonical_links, fetcher):
    new_count = 0
    for job in jobs:
        canonical = canonicalize_link(job["link"])
        if job["id"] in existing_ids or canonical in existing_canonical_links:
            continue

        if is_blocked_company(job["company"]):
            print(f"  Blocked company, skipping classification: {job['company']}")
            lowered = job["company"].strip().lower()
            if lowered in BLOCKED_COMPANIES:
                reason = "blocked company (ICE/surveillance)"
            else:
                reason = "defense contractor / government sector (dealbreaker)"
            classification = {"relevant": False, "score": 1, "reason": reason}
        else:
            print(f"  Fetching posting text: {job['company']} — {job['title']}")
            status_code, description = fetcher.fetch(job["link"])
            status = posting_status(status_code, description)
            if status in ("dead", "closed"):
                print(f"  Skipping ({status}), not classifying or saving: {job['company']} — {job['title']}")
                continue
            print(f"  Classifying: {job['company']} — {job['title']}")
            classification = classify_job(job, description=description)

        client.table("job_postings").insert({
            "id": job["id"],
            "company": job["company"],
            "title": job["title"],
            "location": job["location"],
            "link": job["link"],
            "source": job["source"],
            "date_posted": job["date_posted"],
            "date_scraped": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "status": "not applied",
            "relevance_score": classification.get("score"),
            "relevance_reason": classification.get("reason", ""),
        }).execute()

        try:
            client.table("status_history").insert({
                "job_id": job["id"],
                "old_status": "n/a",
                "new_status": "not applied",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception as e:
            print(f"  Warning: job added but history logging failed: {e}")

        existing_ids.add(job["id"])
        existing_canonical_links.add(canonical)
        new_count += 1
    return new_count

if __name__ == "__main__":
    print("Fetching from sources...")
    speedyapply_jobs = speedyapply.get_jobs()
    print(f"  speedyapply: {len(speedyapply_jobs)} postings match filters")
    newgrad2027_jobs = newgrad2027.get_jobs()
    print(f"  newgrad2027: {len(newgrad2027_jobs)} postings match filters")
    jobs = speedyapply_jobs + newgrad2027_jobs
    print(f"{len(jobs)} total postings match filters")

    print("Connecting to Supabase...")
    client = get_client()

    print("Checking which ones are already saved...")
    existing_ids, existing_canonical_links = get_existing_ids(client)
    print(f"{len(existing_ids)} already in the sheet")

    print("Adding new postings...")
    with JobTextFetcher() as fetcher:
        added = add_new_jobs(client, jobs, existing_ids, existing_canonical_links, fetcher)
    print(f"\nAdded {added} new posting(s) to the sheet.")