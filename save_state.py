from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.reddit.com/login")
    input("Log in manually in the opened browser window, then press Enter here…")
    context.storage_state(path="auth.json")
    browser.close()