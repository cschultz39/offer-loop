# ------------- imports --------------------------
import json
from fetch_job_text import JobTextFetcher, needs_playwright

CACHE_PATH = "extraction_cache.json"
SAMPLE_SIZE = 8


def get_sample_thin_jobs(n):
    """Pulls a small, mixed sample from the thin bucket — some Ashby/Workday,
    some not — so we can eyeball both paths in one test run."""
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        cache = json.load(f)

    thin_entries = [e for e in cache.values() if e["bucket"] == "thin"]

    js_sample = [e for e in thin_entries if needs_playwright(e["link"])][: n // 2]
    other_sample = [e for e in thin_entries if not needs_playwright(e["link"])][: n // 2]

    return js_sample + other_sample


def run_test():
    sample = get_sample_thin_jobs(SAMPLE_SIZE)
    print(f"Testing extraction on {len(sample)} postings...\n")

    with JobTextFetcher() as fetcher:
        for entry in sample:
            route = "playwright" if needs_playwright(entry["link"]) else "requests"
            status_code, text = fetcher.fetch(entry["link"])
            word_count = len(text.split()) if text else 0

            print(f"{entry['company']} — {route} — status {status_code} — {word_count} words")
            if text:
                preview = text[:300]
                print(f"    preview: {preview}...")
            else:
                print("    preview: (extraction failed)")
            print()


if __name__ == "__main__":
    run_test()