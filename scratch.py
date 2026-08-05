from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent="Mozilla/5.0")
    page.goto("https://careers.dat.com/jobs/?gh_jid=6007145004", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    print(f"Frames found: {len(page.frames)}")
    for frame in page.frames:
        print(f"  {frame.url}")

    browser.close()