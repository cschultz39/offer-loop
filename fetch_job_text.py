# ------------- imports --------------------------
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

JS_RENDERED_DOMAINS = ["ashbyhq.com", "myworkdayjobs.com", "metacareers.com"]

DEAD_LINK_PATTERNS = [
    "page you are looking for doesn't exist",
    "page is no longer available",
]

def is_dead_link_text(text):
    lowered = text.lower()
    return any(pattern in lowered for pattern in DEAD_LINK_PATTERNS)

def get_domain(url):
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return "unknown"


def needs_playwright(url):
    domain = get_domain(url)
    return any(js_domain in domain for js_domain in JS_RENDERED_DOMAINS)

def extract_with_requests(url, timeout=10):
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    except requests.RequestException:
        return None, None

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    if text and is_dead_link_text(text):
        return resp.status_code, None  # treat as no usable content, not a real description
    return resp.status_code, text

class JobTextFetcher:
    """Reusable fetcher — keeps one Playwright browser instance alive across
    many calls, since launching a new browser per job is slow at scale.
    Use as a context manager: `with JobTextFetcher() as fetcher: ...`"""

    def __init__(self):
        self._playwright = None
        self._browser = None

    def __enter__(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch()
        return self

    def __exit__(self, *args):
        self._browser.close()
        self._playwright.stop()

    def fetch(self, url):
        if needs_playwright(url):
            return self._extract_with_playwright(url)
        return extract_with_requests(url)

    def _extract_with_playwright(self, url, timeout=15000):
        try:
            page = self._browser.new_page(user_agent="Mozilla/5.0")
            try:
                page.goto(url, timeout=timeout, wait_until="networkidle")
            except Exception:
                # some pages (e.g. Workday) never go fully idle — fall back to
                # waiting for DOM content plus a fixed pause for JS to populate it
                page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
            html = page.content()
            page.close()
        except Exception as e:
            print(f"  Playwright extraction failed for {url}: {e}")
            return None, None

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        if text and is_dead_link_text(text):
            return 200, None  # treat as no usable content, not a real description
        return 200, text