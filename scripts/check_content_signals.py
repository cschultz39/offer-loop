# ------------- imports --------------------------
import json

CACHE_PATH = "addressable_extraction_cache.json"

JOB_CONTENT_SIGNALS = [
    "responsibilit", "requirement", "qualif", "you will", "you'll",
    "we're looking for", "about the role", "compensation", "employment type",
]


def looks_like_real_posting(text, min_signals=1):
    """A page is treated as a real job description if it contains at least
    one job-specific signal phrase — length alone doesn't reliably separate
    real postings from boilerplate nav pages that happen to be long."""
    if not text:
        return False
    lowered = text.lower()
    signal_count = sum(1 for phrase in JOB_CONTENT_SIGNALS if phrase in lowered)
    return signal_count >= min_signals


def word_count_bucket(wc):
    if wc == 0:
        return "0 (failed)"
    elif wc < 50:
        return "1-49"
    elif wc < 100:
        return "50-99"
    elif wc < 200:
        return "100-199"
    elif wc < 500:
        return "200-499"
    else:
        return "500+"


def run_check():
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        results = json.load(f)

    # cross-tab: word-count bucket -> {passed, failed}
    crosstab = {}
    passed_total = 0
    failed_total = 0

    for entry in results.values():
        bucket = word_count_bucket(entry["word_count"])
        passed = looks_like_real_posting(entry["text"])

        if bucket not in crosstab:
            crosstab[bucket] = {"passed": 0, "failed": 0}
        crosstab[bucket]["passed" if passed else "failed"] += 1

        if passed:
            passed_total += 1
        else:
            failed_total += 1

    total = len(results)
    print(f"Content-signal check across {total} postings\n")
    print(f"Passed (treated as real postings): {passed_total} ({passed_total/total*100:.1f}%)")
    print(f"Failed (treated as junk/boilerplate): {failed_total} ({failed_total/total*100:.1f}%)\n")

    print("By word-count bucket:")
    bucket_order = ["0 (failed)", "1-49", "50-99", "100-199", "200-499", "500+"]
    for bucket in bucket_order:
        if bucket not in crosstab:
            continue
        counts = crosstab[bucket]
        bucket_total = counts["passed"] + counts["failed"]
        print(f"  {bucket}: {bucket_total} total — {counts['passed']} passed, {counts['failed']} failed")

    # flag the interesting edge cases specifically
    print("\nWorth a look — 500+ words but FAILED the signal check (signal list may be too narrow):")
    for entry in results.values():
        if entry["word_count"] >= 500 and not looks_like_real_posting(entry["text"]):
            print(f"    {entry['company']} ({entry['word_count']} words)")

    print("\nWorth a look — under 50 words but PASSED the signal check (possible false positive):")
    for entry in results.values():
        if 0 < entry["word_count"] < 50 and looks_like_real_posting(entry["text"]):
            print(f"    {entry['company']} ({entry['word_count']} words)")


if __name__ == "__main__":
    run_check()