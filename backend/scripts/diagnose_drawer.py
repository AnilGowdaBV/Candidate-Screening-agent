import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from playwright.async_api import async_playwright

SEARCH_URL = "https://www.instahyre.com/employer/search/results/?boolean_query=(+(+Playwright+OR+Cypress+OR+WebdriverIO+)+AND+(+Typescript+OR+javascript+)+)&current_locations=North+India,Anywhere+in+Karnataka,West+India,East+India&entire_resume=true&filter_date=2026-10-30T10:20:05&hide_viewed_by_others=false&hide_viewed_by_self=false&job_functions=1:5&large_company_size=false&limit=30&limit_count=true&management_role=1&mid_company_size=false&must_match_education=false&notice_period=0&offset=0&pg_education=0&salary_max=11&salary_min=4&search_skill_option=1&selected_search_option=3&small_company_size=false&status=1&ug_education=0&workex_max=4&workex_min=2"

async def main():
    profile_dir = Path("backend/data/browser_profile").resolve()
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(6)
        print("Final URL:", page.url)
        print("Page Title:", await page.title())

        # Check if login or cloudflare
        text = await page.evaluate("() => document.body ? document.body.innerText.substring(0, 500) : ''")
        print("Body Text Preview:\n", text)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
