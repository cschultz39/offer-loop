# --------------------------------
#            imports
# --------------------------------
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from pydantic import BaseModel

import sys
import os
import secrets

# allows main to access sheet_tools while living folder below repo root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_tools import get_status_counts, search_jobs, mark_status, get_status_history_weekly, mark_not_interested
from agent import ask_agent

API_SECRET = os.environ["API_SECRET"]

async def verify_secret(x_api_key: str = Header(...)):
    if not secrets.compare_digest(x_api_key, API_SECRET):
        raise HTTPException(status_code=401, detail="Unauthorized")

app = FastAPI(title="Job Search Agent API", dependencies=[Depends(verify_secret)])
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------
#           endpoints
# --------------------------------
@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/metrics")
def get_metrics():
    return get_status_counts()

@app.get("/jobs")
def get_jobs(
    status: Optional[str] = None,
    min_score: Optional[int] = None,
    company: Optional[str] = None,
    location: Optional[str] = None,
    source: Optional[str] = None,
    title: Optional[str] = None,
    date_posted_after: Optional[str] = None,
    date_posted_before: Optional[str] = None,
    date_scraped_after: Optional[str] = None,
    date_scraped_before: Optional[str] = None,
    limit: int = 10,
):
    return search_jobs(
        status=status,
        min_score=min_score,
        company=company,
        location=location,
        source=source,
        title=title,
        date_posted_after=date_posted_after,
        date_posted_before=date_posted_before,
        date_scraped_after=date_scraped_after,
        date_scraped_before=date_scraped_before,
        limit=limit,
    )

class StatusUpdate(BaseModel):
    job_id: str
    new_status: str
@app.patch("/jobs/status")
def update_job_status(update: StatusUpdate):
    result = mark_status(update.job_id, update.new_status)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

class NotInterestedRequest(BaseModel):
    job_id: str
@app.patch("/jobs/not-interested")
def update_not_interested(request: NotInterestedRequest):
    result = mark_not_interested(request.job_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@app.get("/history")
def get_history():
    return get_status_history_weekly()

class ChatRequest(BaseModel):
    message: str
    conversation_history: list = []
@app.post("/chat")
def chat(request: ChatRequest):
    return ask_agent(request.message, request.conversation_history)

