import asyncio
import sys
from pathlib import Path
import re

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from playwright.async_api import async_playwright

CANDIDATE_URL = "https://www.instahyre.com/candidate/2596989/"

async def main():
    profile_dir = Path("backend/data/browser_profile").resolve()
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        print(f"Opening candidate: {CANDIDATE_URL}...")
        await page.goto(CANDIDATE_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)
        print("Current URL:", page.url)
        print("Title:", await page.title())

        # Save screenshot
        await page.screenshot(path="backend/scratch_candidate.png")

        # Get all text
        body_text = await page.evaluate("() => document.body.innerText")
        print("Body text length:", len(body_text))

        # Check for github in text
        gh_matches = re.findall(r"(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_\-\.\/]+", body_text, re.IGNORECASE)
        print("Regex matches in body text:", gh_matches)

        # Check all links
        links = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a')).map(a => ({
                href: a.href || a.getAttribute('href'),
                text: a.innerText.trim(),
                title: a.title,
                class: a.className
            }));
        }""")
        gh_links = [l for l in links if l.get("href") and "github" in l["href"].lower()]
        print("GitHub <a> links:", gh_links)

        # Check Angular candidate data
        ang = await page.evaluate("""() => {
            if (!window.angular) return 'No angular';
            const m = document.querySelector('.candidate-profile, #resume-modal-block, .application-modal-wrap') || document.body;
            const sc = angular.element(m).scope();
            if (!sc) return 'No scope';
            const c = sc.candidate || sc.cand || sc.resumeCandidate;
            if (!c) return 'No candidate on scope';
            return {
                name: c.display_name,
                social_accounts: c.social_accounts,
                fc_github_url: c.fc_github_url,
                github_url: c.github_url,
                social_links: c.social_links
            };
        }""")
        print("Angular candidate info:", ang)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
