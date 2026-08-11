import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client

STATUS_OPTIONS = [
    "not applied", "applied", "oa", "behavioral interview", "technical interview", "offer", "rejected", "withdrawn", "not interested", "closed",
]

CENTRAL_TZ = ZoneInfo("America/Chicago")

_client = None

def get_client():
    global _client
    if _client is None:
        _client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    return _client

def search_jobs(status=None, min_score=None, company=None, location=None, source=None, title=None,
                 date_posted_after=None, date_posted_before=None,
                 date_scraped_after=None, date_scraped_before=None, limit=10):
    query = get_client().table("job_postings").select("*")
    if status is not None:
        query = query.ilike("status", status)
    if min_score is not None:
        query = query.gte("relevance_score", min_score)
    if company is not None:
        query = query.ilike("company", f"%{company}%")
    if location is not None:
        query = query.ilike("location", f"%{location}%")
    if source is not None:
        query = query.ilike("source", f"%{source}%")
    if title is not None:
        query = query.ilike("title", f"%{title}%")
    if date_posted_after is not None:
        query = query.gte("date_posted", date_posted_after)
    if date_posted_before is not None:
        query = query.lte("date_posted", date_posted_before)
    if date_scraped_after is not None:
        query = query.gte("date_scraped", date_scraped_after)
    if date_scraped_before is not None:
        query = query.lte("date_scraped", date_scraped_before)
    result = query.order("relevance_score", desc=True).limit(limit).execute()
    return result.data

def get_status_counts():
    counts = {status: 0 for status in STATUS_OPTIONS}
    result = get_client().table("job_postings").select("status").execute()
    for row in result.data:
        if row.get("status") in counts:
            counts[row["status"]] += 1
    return counts

def get_status_history_weekly():
    events = get_client().table("status_history").select("*").order("timestamp").execute().data

    if not events:
        return []

    def parse_ts(ts_str):
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).astimezone(CENTRAL_TZ)

    events = sorted(events, key=lambda e: parse_ts(e["timestamp"]))

    job_status = {}
    first_week_start = parse_ts(events[0]["timestamp"]).date()
    first_week_start -= timedelta(days=first_week_start.weekday())
    current_week_start = datetime.now(CENTRAL_TZ).date()
    current_week_start -= timedelta(days=current_week_start.weekday())

    weekly_snapshots = []
    week_start = first_week_start
    event_idx = 0
    while week_start <= current_week_start:
        week_end = week_start + timedelta(days=7)
        while event_idx < len(events) and parse_ts(events[event_idx]["timestamp"]).date() < week_end:
            e = events[event_idx]
            job_status[e["job_id"]] = e["new_status"]
            event_idx += 1

        snapshot = {status: 0 for status in STATUS_OPTIONS}
        for status in job_status.values():
            if status in snapshot:
                snapshot[status] += 1
        weekly_snapshots.append({"week_of": week_start.strftime("%Y-%m-%d"), **snapshot})

        week_start = week_end

    return weekly_snapshots

def mark_status(job_id, new_status):
    if new_status not in STATUS_OPTIONS:
        return {"success": False, "error": f"'{new_status}' is not a valid status. Must be one of: {', '.join(STATUS_OPTIONS)}"}

    client = get_client()
    existing = client.table("job_postings").select("status").eq("id", job_id).execute()
    if not existing.data:
        return {"success": False, "error": "job_id not found"}

    old_status = existing.data[0]["status"]
    client.table("job_postings").update({"status": new_status}).eq("id", job_id).execute()

    try:
        client.table("status_history").insert({
            "job_id": job_id,
            "old_status": old_status,
            "new_status": new_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        print(f"Warning: status update succeeded but history logging failed: {e}")

    return {"success": True}

def mark_not_interested(job_id):
    client = get_client()
    existing = client.table("job_postings").select("status").eq("id", job_id).execute()
    if not existing.data:
        return {"success": False, "error": "job_id not found"}

    old_status = existing.data[0]["status"]
    client.table("job_postings").update({
        "status": "not interested",
        "relevance_score": 1,
        "relevance_reason": "candidate is not interested",
    }).eq("id", job_id).execute()

    try:
        client.table("status_history").insert({
            "job_id": job_id,
            "old_status": old_status,
            "new_status": "not interested",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        print(f"Warning: status update succeeded but history logging failed: {e}")

    return {"success": True}

def mark_closed(job_id, detected_status):
    """detected_status is 'dead' or 'closed', as returned by posting_status() —
    recorded in relevance_reason so it's visible without a new column."""
    client = get_client()
    existing = client.table("job_postings").select("status").eq("id", job_id).execute()
    if not existing.data:
        return {"success": False, "error": "job_id not found"}

    old_status = existing.data[0]["status"]
    client.table("job_postings").update({
        "status": "closed",
        "relevance_score": 1,
        "relevance_reason": f"posting no longer available ({detected_status}, detected on recheck)",
    }).eq("id", job_id).execute()

    try:
        client.table("status_history").insert({
            "job_id": job_id,
            "old_status": old_status,
            "new_status": "closed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        print(f"Warning: status update succeeded but history logging failed: {e}")

    return {"success": True}