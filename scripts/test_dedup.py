from db_tools import get_client
from collect_github import canonicalize_link, get_existing_ids
from sources import speedyapply, newgrad2027

client = get_client()
existing_ids, existing_canonical_links = get_existing_ids(client)

speedyapply_jobs = speedyapply.get_jobs()
newgrad2027_jobs = newgrad2027.get_jobs()
all_jobs = speedyapply_jobs + newgrad2027_jobs

exact_id_matches = []
canonical_only_matches = []
new_jobs = []
seen_canonical_this_run = set()

for job in all_jobs:
    canonical = canonicalize_link(job["link"])
    if job["id"] in existing_ids:
        exact_id_matches.append(job)
    elif canonical in existing_canonical_links or canonical in seen_canonical_this_run:
        canonical_only_matches.append(job)
    else:
        new_jobs.append(job)
    seen_canonical_this_run.add(canonical)

print(f"speedyapply: {len(speedyapply_jobs)} | newgrad2027: {len(newgrad2027_jobs)} | total: {len(all_jobs)}")
print(f"\nExact id match (already in DB, same id):        {len(exact_id_matches)}")
print(f"Canonical-only match (cross-source or same-run dup): {len(canonical_only_matches)}")
print(f"Genuinely new:                                    {len(new_jobs)}")

print("\n--- sample of canonical-only matches ---")
for job in canonical_only_matches[:10]:
    print(f"  [{job['source']}] {job['company']} — {job['title']}")
    print(f"    id: {job['id']}")
    print(f"    canonical: {canonicalize_link(job['link'])}")