import os
import json
from dotenv import load_dotenv
load_dotenv()

from anthropic import Anthropic
from db_tools import search_jobs, mark_status

from datetime import datetime
from zoneinfo import ZoneInfo

CENTRAL_TZ = ZoneInfo("America/Chicago")

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

TOOLS = [
    {
        "name": "search_jobs",
        "description": "Search saved job postings, optionally filtered by status, minimum relevance score, company, location, source, title, or date ranges for when the job was posted or scraped. Returns results sorted by relevance score, highest first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter by status, e.g. 'not applied', 'applied', 'interviewing'"},
                "min_score": {"type": "integer", "description": "Minimum relevance score, 1-10"},
                "company": {"type": "string", "description": "Filter by company name (partial match)"},
                "location": {"type": "string", "description": "Filter by location (partial match), e.g. 'Chicago', 'Remote'"},
                "source": {"type": "string", "description": "Filter by the source list the posting came from, e.g. 'speedyapply', 'newgrad2027'"},
                "title": {"type": "string", "description": "Filter by job title (partial match), e.g. 'FDE', 'Software Engineer'"},
                "date_posted_after": {"type": "string", "description": "Only jobs posted on or after this date, format YYYY-MM-DD"},
                "date_posted_before": {"type": "string", "description": "Only jobs posted on or before this date, format YYYY-MM-DD"},
                "date_scraped_after": {"type": "string", "description": "Only jobs scraped on or after this date, format YYYY-MM-DD"},
                "date_scraped_before": {"type": "string", "description": "Only jobs scraped on or before this date, format YYYY-MM-DD"},
                "limit": {"type": "integer", "description": "Max number of results to return, default 10"},
            },
        },
    },
    {
        "name": "mark_status",
        "description": "Update the application status of a specific job posting, identified by its id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "The unique id of the job posting"},
                "new_status": {
                    "type": "string",
                    "enum": ["not applied", "applied", "oa", "behavioral interview", "technical interview", "offer", "rejected", "withdrawn"],
                    "description": "The new application status",
                },
            },
            "required": ["job_id", "new_status"],
        },
    },
]

def run_tool(name, tool_input):
    """Dispatches a tool call by name to the actual Python function."""
    if name == "search_jobs":
        return search_jobs(**tool_input)
    if name == "mark_status":
        return mark_status(**tool_input)
    return {"error": f"unknown tool: {name}"}

def build_system_prompt():
    today = datetime.now(CENTRAL_TZ).strftime("%A, %B %d, %Y")
    return f"""You are a job search assistant helping the user browse and manage saved job postings.

Today's date is {today}. Use this to resolve relative date references in the user's questions (e.g. "posted this week," "scraped in the last 3 days," "posted since Monday") into actual date_posted_after/date_posted_before or date_scraped_after/date_scraped_before values, formatted as YYYY-MM-DD, when calling search_jobs.

When your answer involves specific job postings, don't list out their details (company, title, score, link, status) in your text response — those are rendered separately as cards below your message. Just write a short, natural sentence introducing or summarizing what you found (e.g. "Here are your top matches:" or "Found 3 unapplied jobs at Chicago-based companies:"), and let the cards speak for the specifics.

Only fall back to describing individual job details in text if the user asks a question that isn't well answered by a card list — e.g. comparing two jobs, or asking about a field the cards don't show."""

def ask_agent(user_message, conversation_history=None):
    if conversation_history is None:
        conversation_history = []

    messages = list(conversation_history) + [{"role": "user", "content": user_message}]

    found_jobs = {}

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=build_system_prompt(),
        tools=TOOLS,
        messages=messages,
    )

    while response.stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"  [Claude is calling: {block.name}({block.input})]")
                result = run_tool(block.name, block.input)
                if block.name == "search_jobs" and isinstance(result, list):
                    found_jobs = {job["id"]: job for job in result if job.get("id")}
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=build_system_prompt(),
            tools=TOOLS,
            messages=messages,
        )

    final_text = "".join(block.text for block in response.content if block.type == "text")

    updated_history = conversation_history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": final_text},
    ]

    return {"text": final_text, "jobs": list(found_jobs.values()), "conversation_history": updated_history}