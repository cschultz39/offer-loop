# ats_apis.py
"""
Direct API access for ATS platforms that expose the same JSON their own
frontend uses to render job postings. Bypasses Playwright entirely for
Greenhouse and Workday, which were the two least reliable Playwright routes
in testing (Workday: ~13% silent zero-word-count failures; Greenhouse
iframe-hunting: inconsistent on embeds like DigiCert / Fulcrum GT).
"""

import re
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}


def _html_to_text(html):
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    text = " ".join(soup.get_text(separator=" ").split())
    return text or None


# --------------------------- Greenhouse ---------------------------

GREENHOUSE_BOARD_DOMAINS = ("boards.greenhouse.io", "job-boards.greenhouse.io")

# Patterns that can appear in the *static* HTML of a company's careers page
# even when the actual description is JS-rendered inside an iframe — the
# iframe `src` (or widget `data-token`) attribute itself doesn't need JS to
# exist in the page source, so a plain `requests.get` + regex can find it.
GH_EMBED_TOKEN_PATTERNS = [
    # covers both embed/job_app?for=... and embed/job_board/js?for=...
    re.compile(r"greenhouse\.io/embed/job_(?:app|board/js)\?(?:for|token)=([\w-]+)"),
    re.compile(r"boards\.greenhouse\.io/([\w-]+)/jobs/\d+"),
    re.compile(r"job-boards\.greenhouse\.io/([\w-]+)/jobs/\d+"),
    re.compile(r'data-token=["\']([\w-]+)["\']'),  # Greenhouse's JS-widget embed
]


def is_greenhouse_url(url):
    domain = urlparse(url).netloc
    return any(d in domain for d in GREENHOUSE_BOARD_DOMAINS) or "gh_jid=" in url


def _parse_greenhouse_direct(url):
    """URL already points at boards.greenhouse.io or job-boards.greenhouse.io —
    board token and job id are both sitting in the path, no fetch needed."""
    parts = urlparse(url)
    if not any(d in parts.netloc for d in GREENHOUSE_BOARD_DOMAINS):
        return None
    match = re.match(r"^/([^/]+)/jobs/(\d+)", parts.path)
    if not match:
        return None
    return {"board_token": match.group(1), "job_id": match.group(2)}


def _parse_greenhouse_embed(url, timeout=10):
    """URL is a company's own page with a ?gh_jid=<id> embed. The job id is
    the query param itself; the board token requires one plain-HTML fetch of
    the parent page (still no browser)."""
    qs = parse_qs(urlparse(url).query)
    job_id = qs.get("gh_jid", [None])[0]
    if not job_id:
        return None

    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None

    for pattern in GH_EMBED_TOKEN_PATTERNS:
        match = pattern.search(resp.text)
        if match:
            return {"board_token": match.group(1), "job_id": job_id}
    return None


def fetch_greenhouse_job(url, timeout=10):
    """Returns extracted description text, or None if this isn't a
    Greenhouse URL or the API lookup failed — caller should fall back to
    Playwright in that case."""
    if not is_greenhouse_url(url):
        return None

    identifiers = _parse_greenhouse_direct(url) or _parse_greenhouse_embed(url, timeout)
    if not identifiers:
        return None

    api_url = (
        f"https://boards-api.greenhouse.io/v1/boards/"
        f"{identifiers['board_token']}/jobs/{identifiers['job_id']}"
    )
    try:
        resp = requests.get(
            api_url, params={"content": "true"}, headers=DEFAULT_HEADERS, timeout=timeout
        )
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None

    return _html_to_text(resp.json().get("content", ""))


# --------------------------- Workday ---------------------------

WORKDAY_HOST_PATTERN = re.compile(r"^([\w-]+)\.(wd\d+)\.myworkdayjobs\.com$")

# Description text has moved around slightly across Workday tenant/versions —
# search a few known key names rather than hard-coding one path.
WORKDAY_DESCRIPTION_KEYS = ("jobDescription", "description")


def is_workday_url(url):
    return bool(WORKDAY_HOST_PATTERN.match(urlparse(url).netloc))


def _parse_workday_url(url):
    """Tenant, data-center, site, and req path are all already sitting in the
    job URL you scraped — nothing to fetch to figure this out."""
    parts = urlparse(url)
    host_match = WORKDAY_HOST_PATTERN.match(parts.netloc)
    if not host_match:
        return None
    tenant, wd_server = host_match.groups()

    path_parts = [p for p in parts.path.split("/") if p]
    if "job" not in path_parts:
        return None
    job_index = path_parts.index("job")
    if job_index == 0:
        return None
    site = path_parts[job_index - 1]
    external_path = "/".join(path_parts[job_index + 1:])
    if not external_path:
        return None

    return {
        "tenant": tenant,
        "wd_server": wd_server,
        "site": site,
        "external_path": external_path,
    }


def _find_str_field(obj, keys):
    """Recursively search a parsed JSON response for the first matching
    description field — guards against Workday's JSON shape drifting
    between tenant/versions."""
    if isinstance(obj, dict):
        for k in keys:
            v = obj.get(k)
            if isinstance(v, str) and v:
                return v
        for v in obj.values():
            found = _find_str_field(v, keys)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_str_field(item, keys)
            if found:
                return found
    return None


def fetch_workday_job(url, timeout=10):
    if not is_workday_url(url):
        return None
    identifiers = _parse_workday_url(url)
    if not identifiers:
        return None

    base = f"https://{identifiers['tenant']}.{identifiers['wd_server']}.myworkdayjobs.com"
    human_url = f"{base}/en-US/{identifiers['site']}/job/{identifiers['external_path']}"
    api_url = (
        f"{base}/wday/cxs/{identifiers['tenant']}/{identifiers['site']}/job/"
        f"{identifiers['external_path']}"
    )

    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    try:
        # Visiting the human-facing page first establishes the cookies
        # Workday's bot-protection expects before it'll answer the CXS API
        # directly — hitting the API cold returns a 403 even on a correct URL.
        session.get(human_url, timeout=timeout)
    except requests.RequestException:
        pass  # if this fails, still try the API call below — it may work anyway

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Accept-Language": "en-US",
        "Referer": human_url,
    }

    try:
        resp = session.get(api_url, headers=headers, timeout=timeout)
    except requests.RequestException:
        return None

    if resp.status_code == 200:
        html_desc = _find_str_field(resp.json(), WORKDAY_DESCRIPTION_KEYS)
        return _html_to_text(html_desc)

    # 403 here means Cloudflare bot-management, not a fixable client issue —
    # 404 means the requisition is genuinely closed. Either way: None,
    # falls through to Playwright as designed.
    return None


# --------------------------- entry point ---------------------------

def fetch_via_ats_api(url, timeout=10):
    """Tries all known direct-API routes. Returns text or None — None means
    'not a known platform, or the API call didn't pan out', so the caller
    should fall back to its normal requests/Playwright path."""
    if is_greenhouse_url(url):
        return fetch_greenhouse_job(url, timeout)
    if is_workday_url(url):
        return fetch_workday_job(url, timeout)
    return None