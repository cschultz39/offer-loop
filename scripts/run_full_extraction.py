# ------------- imports --------------------------
import json
import time
from collect_github import BLOCKED_COMPANIES
from fetch_job_text import JobTextFetcher, needs_playwright

SOURCE_CACHE_PATH = "extraction_cache.json"
OUTPUT_CACHE_PATH = "addressable_extraction_cache.json"

DEALBREAKER_KEYWORDS = [
    "raytheon", "boeing", "northrop grumman", "lockheed",
    "gdit", "leidos", "caci", "booz allen",
]


def is_likely_dealbreaker(company):
    lowered = company.lower()
    if lowered in BLOCKED_COMPANIES:
        return True
    return any(keyword in lowered for keyword in DEALBREAKER_KEYWORDS)


def get_addressable_jobs():
    with open(SOURCE_CACHE_PATH, "r", encoding="utf-8") as f:
        cache = json.load(f)

    return [
        {"id": job_id, **entry}
        for job_id, entry in cache.items()
        if entry["bucket"] == "thin" and not is_likely_dealbreaker(entry["company"])
    ]


def run_full_extraction():
    jobs = get_addressable_jobs()
    print(f"Extracting text for {len(jobs)} addressable postings...\n")

    results = {}
    with JobTextFetcher() as fetcher:
        for i, job in enumerate(jobs, 1):
            route = "playwright" if needs_playwright(job["link"]) else "requests"
            status_code, text = fetcher.fetch(job["link"])
            word_count = len(text.split()) if text else 0

            results[job["id"]] = {
                "company": job["company"],
                "link": job["link"],
                "route": route,
                "status_code": status_code,
                "word_count": word_count,
                "text": text,
            }

            if i % 20 == 0:
                print(f"  ...{i}/{len(jobs)} done")

            time.sleep(0.5 if route == "requests" else 1.5)  # Playwright pages are heavier — space them out more

    with open(OUTPUT_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved {len(results)} results to {OUTPUT_CACHE_PATH}\n")
    print_word_count_distribution(results)


def print_word_count_distribution(results):
    buckets = {
        "0 (failed)": 0,
        "1-49": 0,
        "50-99": 0,
        "100-199": 0,
        "200-499": 0,
        "500+": 0,
    }

    for entry in results.values():
        wc = entry["word_count"]
        if wc == 0:
            buckets["0 (failed)"] += 1
        elif wc < 50:
            buckets["1-49"] += 1
        elif wc < 100:
            buckets["50-99"] += 1
        elif wc < 200:
            buckets["100-199"] += 1
        elif wc < 500:
            buckets["200-499"] += 1
        else:
            buckets["500+"] += 1

    total = len(results)
    print("Word count distribution:")
    for label, count in buckets.items():
        pct = (count / total * 100) if total else 0
        print(f"  {label}: {count} ({pct:.1f}%)")


if __name__ == "__main__":
    run_full_extraction()