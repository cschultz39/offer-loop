"""
Weekly recheck of 'not applied' postings to detect closed/dead listings.
Reuses posting_status() from collect_github.py and JobTextFetcher from
fetch_job_text.py — no new detection logic here.
"""
from fetch_job_text import JobTextFetcher
from collect_github import posting_status
from db_tools import search_jobs, mark_closed


def recheck_not_applied():
    jobs = search_jobs(status="not applied", limit=1000)
    print(f"Rechecking {len(jobs)} 'not applied' postings...")

    closed_count = 0
    with JobTextFetcher() as fetcher:
        for job in jobs:
            print(f"  Checking: {job['company']} — {job['title']}")
            status_code, description = fetcher.fetch(job["link"])
            status = posting_status(status_code, description)

            if status in ("dead", "closed"):
                print(f"    -> {status}, marking closed")
                result = mark_closed(job["id"], status)
                if not result.get("success"):
                    print(f"    Warning: failed to mark closed: {result.get('error')}")
                else:
                    closed_count += 1
            else:
                print("    -> still open")

    print(f"Done. {closed_count} of {len(jobs)} postings marked closed.")


if __name__ == "__main__":
    recheck_not_applied()