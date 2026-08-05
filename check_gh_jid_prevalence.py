# ------------- imports --------------------------
import json
from db_tools import get_client

def check_gh_jid_prevalence():
    result = get_client().table("job_postings").select("id, company, link").execute()
    jobs = result.data

    gh_jid_jobs = [j for j in jobs if "gh_jid=" in j["link"]]

    print(f"{len(gh_jid_jobs)} of {len(jobs)} total postings use the gh_jid embed pattern\n")

    by_company = {}
    for job in gh_jid_jobs:
        by_company.setdefault(job["company"], []).append(job["link"])

    for company, links in sorted(by_company.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"{company}: {len(links)} posting(s)")


if __name__ == "__main__":
    check_gh_jid_prevalence()