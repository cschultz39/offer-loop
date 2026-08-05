# ------------- imports + setup --------------------------
import os
import json
import time
from dotenv import load_dotenv
load_dotenv()

import requests
from bs4 import BeautifulSoup
from db_tools import get_client

CACHE_PATH = "extraction_cache.json"
THIN_TEXT_THRESHOLD = 200  # words — below this, assume the page needs JS to render
CLOSED_PATTERNS = [
    "no longer accepting applications",
    "this position has been filled",
    "posting has expired",
    "job is no longer available",
    "position is closed",
]

def get_all_jobs():
    result = get_client().table("job_postings").select("id, company, link").execute()
    return result.data

def fetch_and_extract(url, timeout=10):
    """Fetches a URL and extracts visible text, stripped of script/nav/footer noise.
    Returns (status_code, text) — (None, None) if the request itself fails."""
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    except requests.RequestException:
        return None, None

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return resp.status_code, text

def classify_extraction(status_code, text):
    """Buckets an extraction as 'good', 'thin' (likely needs JS), 'closed', or 'dead'."""
    if status_code is None or status_code != 200:
        return "dead"

    lowered = text.lower()
    if any(pattern in lowered for pattern in CLOSED_PATTERNS):
        return "closed"

    if len(text.split()) < THIN_TEXT_THRESHOLD:
        return "thin"

    return "good"

def run_diagnostic():
    jobs = get_all_jobs()
    print(f"Checking extraction on {len(jobs)} postings...")

    cache = {}
    results = {"good": 0, "thin": 0, "closed": 0, "dead": 0}

    for i, job in enumerate(jobs, 1):
        status_code, text = fetch_and_extract(job["link"])
        bucket = classify_extraction(status_code, text)
        results[bucket] += 1

        cache[job["id"]] = {
            "company": job["company"],
            "link": job["link"],
            "status_code": status_code,
            "word_count": len(text.split()) if text else 0,
            "bucket": bucket,
            "text": text if bucket == "good" else None,
        }

        if i % 25 == 0:
            print(f"  ...{i}/{len(jobs)} checked")

        time.sleep(0.5)  # stay polite to job boards

    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

    print("\nResults:")
    total = len(jobs)
    for bucket, count in results.items():
        pct = (count / total * 100) if total else 0
        print(f"  {bucket}: {count} ({pct:.1f}%)")

    print(f"\nCached extraction details to {CACHE_PATH}")

if __name__ == "__main__":
    run_diagnostic()