from fetch_job_text import JobTextFetcher
from collect_github import posting_status

known_closed_or_dead = [
    "https://www.digicert.com/careers/?gh_jid=8637536002",  # Greenhouse API returned 404
    "https://bcbst.wd1.myworkdayjobs.com/en-US/external/job/USA-TN-Chattanooga-Remote/Associate-Software-Engineer-II_R-50763",  # Workday API returned 404
]

with JobTextFetcher() as fetcher:
    for url in known_closed_or_dead:
        status_code, text = fetcher.fetch(url)
        print(url[:70], "->", posting_status(status_code, text))