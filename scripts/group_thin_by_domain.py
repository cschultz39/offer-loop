# ------------- imports --------------------------
import json
from collections import defaultdict
from urllib.parse import urlparse

CACHE_PATH = "extraction_cache.json"


def get_domain(url):
    """Extracts a normalized domain from a URL, e.g. 'boards.greenhouse.io'."""
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return "unknown"


def group_thin_by_domain():
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        cache = json.load(f)

    domain_counts = defaultdict(list)
    for job_id, entry in cache.items():
        if entry["bucket"] != "thin":
            continue
        domain = get_domain(entry["link"])
        domain_counts[domain].append(entry["company"])

    # sort by how many thin postings each domain accounts for, most first
    sorted_domains = sorted(domain_counts.items(), key=lambda x: len(x[1]), reverse=True)

    total_thin = sum(len(companies) for _, companies in sorted_domains)
    print(f"{total_thin} thin postings across {len(sorted_domains)} distinct domains\n")

    for domain, companies in sorted_domains:
        unique_companies = sorted(set(companies))
        print(f"{domain}: {len(companies)} postings, {len(unique_companies)} companies")
        # show up to 5 example companies so you can eyeball which employers these are
        preview = ", ".join(unique_companies[:5])
        suffix = ", ..." if len(unique_companies) > 5 else ""
        print(f"    e.g. {preview}{suffix}")


if __name__ == "__main__":
    group_thin_by_domain()