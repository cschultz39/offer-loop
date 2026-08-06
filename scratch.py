# debug_workday_session.py
import requests
from ats_apis import _parse_workday_url, DEFAULT_HEADERS

def debug_session_flow(url):
    print(f"\n--- {url}")
    identifiers = _parse_workday_url(url)
    base = f"https://{identifiers['tenant']}.{identifiers['wd_server']}.myworkdayjobs.com"
    human_url = f"{base}/en-US/{identifiers['site']}/job/{identifiers['external_path']}"
    api_url = f"{base}/wday/cxs/{identifiers['tenant']}/{identifiers['site']}/job/{identifiers['external_path']}"

    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    warmup = session.get(human_url, timeout=10)
    print("warmup status:", warmup.status_code)
    print("cookies received:", dict(session.cookies))

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Accept-Language": "en-US",
        "Referer": human_url,
    }
    resp = session.get(api_url, headers=headers, timeout=10)
    print("api status:", resp.status_code)
    print("api body[:300]:", resp.text[:300])

debug_session_flow("https://nvidia.wd5.myworkdayjobs.com/en-US/nvidiaexternalcareersite/job/US-CA-Santa-Clara/System-Software-Engineer--Dynamo-Triton-Inference-Server---New-College-Grad-2026_JR2020767")