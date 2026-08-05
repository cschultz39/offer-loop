# ------------- imports --------------------------
import json
from collect_github import BLOCKED_COMPANIES

CACHE_PATH = "extraction_cache.json"

# named directly in CLASSIFICATION_PROMPT's dealbreaker examples — same companies
# Claude is already instructed to auto-score 1 regardless of description content
DEALBREAKER_KEYWORDS = [
    "raytheon", "boeing", "northrop grumman", "lockheed",
    "gdit", "leidos", "caci", "booz allen",
]


def is_likely_dealbreaker(company):
    lowered = company.lower()
    if lowered in BLOCKED_COMPANIES:
        return True
    return any(keyword in lowered for keyword in DEALBREAKER_KEYWORDS)


def check_addressable_thin():
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        cache = json.load(f)

    thin_entries = [entry for entry in cache.values() if entry["bucket"] == "thin"]

    already_excluded = [e for e in thin_entries if is_likely_dealbreaker(e["company"])]
    addressable = [e for e in thin_entries if not is_likely_dealbreaker(e["company"])]

    total = len(thin_entries)
    print(f"{total} thin postings total\n")

    print(f"Likely already excluded by company name: {len(already_excluded)} ({len(already_excluded)/total*100:.1f}%)")
    for e in already_excluded:
        print(f"    {e['company']}")

    print(f"\nAddressable — extraction would actually change/improve classification: "
          f"{len(addressable)} ({len(addressable)/total*100:.1f}%)")
    for e in addressable:
        print(f"    {e['company']}")


if __name__ == "__main__":
    check_addressable_thin()