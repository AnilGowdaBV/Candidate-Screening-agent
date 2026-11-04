from pathlib import Path

file_path = Path("backend/app/browser/browser_manager.py")
content = file_path.read_text(encoding="utf-8")

# 1. Update modal opening & direct navigation fallback
old_open_block = '''        # Click View profile button to open drawer if row found
        modal = self.page.locator(".application-modal-wrap, #resume-modal-block").first
        if row:
            view_btn = await row.query_selector('.button-download-resume, a:has-text("View profile"), button:has-text("View profile"), [ng-click*="viewResume"], [ng-click*="showResume"], [ng-click*="openResume"], .view-profile')
            if view_btn:
                await view_btn.scroll_into_view_if_needed()
                await view_btn.click(force=True)
                await asyncio.sleep(1.5)
            # Fallback to candidate name click if modal not open
            if await modal.count() == 0 or not await modal.is_visible():
                name_link = await row.query_selector(SEARCH_SELECTORS["candidate_name"])
                if name_link:
                    await name_link.click(force=True)
                    await asyncio.sleep(1.5)
        elif profile_url and profile_url != self.page.url:
            await self.page.goto(profile_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)'''

new_open_block = '''        # Click View profile button to open drawer if row found
        modal = self.page.locator(".application-modal-wrap, #resume-modal-block").first
        modal_opened = False
        if row:
            view_btn = await row.query_selector('.button-download-resume, a:has-text("View profile"), button:has-text("View profile"), [ng-click*="viewResume"], [ng-click*="showResume"], [ng-click*="openResume"], .view-profile, [ng-click*="Candidate"]')
            if view_btn:
                await view_btn.scroll_into_view_if_needed()
                await view_btn.click(force=True)
                await asyncio.sleep(1.5)
            if await modal.count() > 0 and await modal.is_visible():
                modal_opened = True
            else:
                name_link = await row.query_selector(SEARCH_SELECTORS["candidate_name"])
                if name_link:
                    await name_link.click(force=True)
                    await asyncio.sleep(1.5)
                if await modal.count() > 0 and await modal.is_visible():
                    modal_opened = True

        # Bulletproof fallback: If modal drawer is not open, navigate directly to candidate profile
        if not modal_opened and profile_url and profile_url != self.page.url:
            logger.info("Modal drawer not open from card click. Navigating directly to profile: %s", profile_url)
            try:
                await self.page.goto(profile_url, wait_until="domcontentloaded", timeout=25000)
                await asyncio.sleep(2.5)
            except Exception as nav_e:
                logger.warning("Direct profile navigation warning: %s", nav_e)'''

assert old_open_block in content, "old_open_block not found"
content = content.replace(old_open_block, new_open_block, 1)

# 2. Update close_candidate_modal to go_back if on direct /candidate/ page
old_close_block = '''    async def close_candidate_modal(self) -> None:
        """Close candidate profile drawer/modal to restore search view for next candidate."""
        if not self.page:
            return
        try:
            modal = self.page.locator(".application-modal-wrap, #resume-modal-block").first'''

new_close_block = '''    async def close_candidate_modal(self) -> None:
        """Close candidate profile drawer/modal to restore search view for next candidate."""
        if not self.page:
            return
        try:
            # If direct navigation to /candidate/ page was used, go back to restore search page
            if "/candidate/" in self.page.url and "/search/results" not in self.page.url:
                try:
                    await self.page.go_back(wait_until="domcontentloaded", timeout=20000)
                    await asyncio.sleep(1.5)
                    await self.ensure_search_job_selected()
                    return
                except Exception as gb_e:
                    logger.warning("go_back warning: %s", gb_e)

            modal = self.page.locator(".application-modal-wrap, #resume-modal-block").first'''

assert old_close_block in content, "old_close_block not found"
content = content.replace(old_close_block, new_close_block, 1)

# 3. Increase Cloudflare check to 12 iterations
old_cf = '''        # Give Cloudflare verification up to 6 seconds to complete if encountered
        for _ in range(6):
            title = (await self.page.title()).lower()
            if "just a moment" not in title and "security verification" not in title:
                break
            await asyncio.sleep(1)'''

new_cf = '''        # Give Cloudflare verification up to 12 seconds to complete if encountered
        for _ in range(12):
            title = (await self.page.title()).lower()
            if "just a moment" not in title and "security verification" not in title:
                break
            await asyncio.sleep(1)'''

content = content.replace(old_cf, new_cf)

file_path.write_text(content, encoding="utf-8", newline="\r\n")
print("Successfully updated browser_manager.py with direct navigation fallback!")
