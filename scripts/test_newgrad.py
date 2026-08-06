from sources.newgrad2027 import fetch_markdown, RAW_URL

text = fetch_markdown()
print(f"Fetched {len(text)} characters from {RAW_URL}")
print("---first 500 chars---")
print(text[:500])

lines = text.split("\n")
print(f"\n{len(lines)} lines total")

header_lines = [
    (i, line) for i, line in enumerate(lines)
    if line.strip().startswith("|") and "Company" in line and "Role" in line
]
print(f"\nHeader lines found: {len(header_lines)}")
for i, line in header_lines[:3]:
    print(f"  line {i}: {line[:150]}")

# peek at a few lines right after the first header match, if any
if header_lines:
    start = header_lines[0][0]
    print(f"\n--- lines {start} to {start+5} ---")
    for line in lines[start:start+6]:
        print(repr(line[:200]))