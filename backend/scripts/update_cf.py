from pathlib import Path

file_path = Path("backend/app/browser/browser_manager.py")
content = file_path.read_text(encoding="utf-8")

# 1. Update user agent in launch_persistent_context
old_launch = '''        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            args=["--disable-blink-features=AutomationControlled"],
        )'''

new_launch = '''        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            viewport={"width": 1366, "height": 768},
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )'''

assert old_launch in content, "old_launch not found"
content = content.replace(old_launch, new_launch, 1)

# 2. Add Cloudflare wait inside inspect_candidate_profile right after opening modal/navigating
old_inspect_wait = '''        # Wait up to 4.5s for modal and resume content or Angular scope to populate
        for _ in range(9):'''

new_inspect_wait = '''        # Wait for Cloudflare if verification screen is shown
        for _ in range(15):
            title = (await self.page.title()).lower()
            if "just a moment" not in title and "security verification" not in title:
                break
            await asyncio.sleep(1)

        # Wait up to 6s for modal and resume content or Angular scope to populate
        for _ in range(12):'''

assert old_inspect_wait in content, "old_inspect_wait not found"
content = content.replace(old_inspect_wait, new_inspect_wait, 1)

file_path.write_text(content, encoding="utf-8", newline="\r\n")
print("Successfully updated browser_manager.py with Cloudflare wait & clean user-agent!")
