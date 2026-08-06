import sys
from db_tools import get_client

CUTOFF_DATE = "2026-07-24"  # anything earlier than this gets deleted
SOURCE = "newgrad2027"
BATCH_SIZE = 50

def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]

def main():
    confirm = "--confirm" in sys.argv
    client = get_client()

    result = (
        client.table("job_postings")
        .select("id, company, title, date_posted, status")
        .eq("source", SOURCE)
        .lt("date_posted", CUTOFF_DATE)
        .execute()
    )
    old_jobs = result.data

    if not old_jobs:
        print(f"No {SOURCE} postings found before {CUTOFF_DATE}. Nothing to do.")
        return

    print(f"Found {len(old_jobs)} {SOURCE} posting(s) before {CUTOFF_DATE}:\n")
    for job in old_jobs:
        print(f"  {job['date_posted']} | {job['company']} — {job['title']} | status: {job['status']}")

    if not confirm:
        print(f"\nDry run only — nothing deleted. Re-run with --confirm to actually delete these {len(old_jobs)} rows (and their status_history entries).")
        return

    job_ids = [job["id"] for job in old_jobs]
    batches = list(chunked(job_ids, BATCH_SIZE))

    print(f"\nDeleting status_history rows for {len(job_ids)} job(s) in {len(batches)} batch(es)...")
    for batch in batches:
        client.table("status_history").delete().in_("job_id", batch).execute()

    print(f"Deleting {len(job_ids)} job_postings row(s) in {len(batches)} batch(es)...")
    for batch in batches:
        client.table("job_postings").delete().in_("id", batch).execute()

    print(f"\nDone. Deleted {len(job_ids)} posting(s) and their status_history entries.")

if __name__ == "__main__":
    main()