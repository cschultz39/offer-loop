# ------------- imports + setup --------------------------
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

import requests
from db_tools import get_client

# ---------------- access tracker -------------------------


# pulls today's jobs directly via a filtered query
def get_todays_jobs(client):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = (
        client.table("job_postings")
        .select("*")
        .eq("date_scraped", today)
        .execute()
    )
    todays = result.data

    # sort by relevance score, highest first — falls back to 0 if
    # score is missing/blank so it doesn't crash on empty strings
    def score_key(r):
        try:
            return int(r.get("relevance_score", 0))
        except (ValueError, TypeError):
            return 0

    todays.sort(key=score_key, reverse=True)
    return todays

# ------------------- slack ----------------------------
def format_message(jobs):
    if not jobs:
        return "The daily loop came up empty!"

    lines = [f"The daily loop found *{len(jobs)} new postings!*\n"]
    for job in jobs:
        score = job.get("relevance_score", "?")
        reason = job.get("relevance_reason", "")
        lines.append(
            f"*{job['company']}* — {job['title']}\n"
            f"  {job['location']} | score: {score}/10 | {reason}\n"
            f"  <{job['link']}|Apply here>\n"
        )
    return "\n".join(lines)

def send_to_slack(message):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    r = requests.post(webhook_url, json={"text": message})
    r.raise_for_status()
    return r.status_code

if __name__ == "__main__":
    print("Connecting to Supabase...")
    client = get_client()

    print("Finding today's new postings...")
    jobs = get_todays_jobs(client)
    print(f"Found {len(jobs)} postings from today")

    print("Formatting and sending to Slack...")
    message = format_message(jobs)
    status = send_to_slack(message)
    print(f"Sent — Slack responded with status {status}")