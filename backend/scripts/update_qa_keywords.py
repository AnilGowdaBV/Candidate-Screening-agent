from pathlib import Path

file_path = Path("backend/app/services/github_service.py")
content = file_path.read_text(encoding="utf-8")

# 1. Update DOMAIN_FRAMEWORKS for qa_automation and qa
old_domain = '''    "qa_automation": ["playwright", "cypress", "selenium", "pytest", "testng", "cucumber", "e2e", "automation"],
    "qa": ["playwright", "cypress", "selenium", "pytest", "testng", "cucumber", "e2e", "automation"],'''

new_domain = '''    "qa_automation": ["playwright", "cypress", "webdriverio", "wdio", "selenium", "pytest", "testng", "cucumber", "e2e", "automation"],
    "qa": ["playwright", "cypress", "webdriverio", "wdio", "selenium", "pytest", "testng", "cucumber", "e2e", "automation"],'''

assert old_domain in content, "old_domain not found"
content = content.replace(old_domain, new_domain, 1)

# 2. Update topics in TECHNOLOGY_SPECS for qa_automation and qa
old_topics = '''            "playwright", "playwright-test", "playwright-testing", "playwright-js", "playwright-ts",
            "qa", "automation", "qa-automation", "test-automation", "e2e", "e2e-testing",
            "testing", "automation-testing", "test-framework", "selenium", "cypress"'''

new_topics = '''            "playwright", "playwright-test", "playwright-testing", "playwright-js", "playwright-ts",
            "cypress", "cypress-io", "cypress-testing", "cypress-e2e",
            "webdriverio", "wdio", "webdriver-io",
            "qa", "automation", "qa-automation", "test-automation", "e2e", "e2e-testing",
            "testing", "automation-testing", "test-framework", "selenium"'''

assert old_topics in content, "old_topics not found"
content = content.replace(old_topics, new_topics)

# 3. Update qa detection block in _inspect_user
old_qa_block = '''        if tech in ("qa_automation", "qa"):
            found_playwright = False
            found_ts = False
            found_js = False
            playwright_repos: List[str] = []
            ts_repos: List[str] = []
            js_repos: List[str] = []
            repos_checked_count = 0

            for repo in repos:
                repo_name = repo.get("name", "")
                repo_name_lower = repo_name.lower()
                repo_desc_lower = (repo.get("description") or "").lower()
                primary_lang = (repo.get("language") or "").strip().lower()
                topics = [t.lower() for t in (repo.get("topics", []) or [])]
                repos_checked_count += 1

                # 1. Playwright check
                if not found_playwright:
                    if (
                        "playwright" in repo_name_lower
                        or "playwright" in repo_desc_lower
                        or any("playwright" in t for t in topics)
                    ):
                        found_playwright = True
                        playwright_repos.append(repo_name)

                # 2. TypeScript (TS) check
                if not found_ts:
                    if primary_lang == "typescript" or any(t in ["typescript", "ts"] for t in topics):
                        found_ts = True
                        ts_repos.append(repo_name)

                # 3. JavaScript (JS) check
                if not found_js:
                    if primary_lang in ["javascript", "node", "nodejs"] or any(
                        t in ["javascript", "js", "node", "nodejs"] for t in topics
                    ):
                        found_js = True
                        js_repos.append(repo_name)

                # Query languages API if TS or JS not yet confirmed
                if (not found_ts or not found_js) and repo.get("languages_url"):
                    try:
                        lang_resp = await client.get(repo.get("languages_url"), headers=headers)
                        if lang_resp.status_code == 200:
                            lang_data = lang_resp.json()
                            if not found_ts and lang_data.get("TypeScript", 0) > 0:
                                found_ts = True
                                ts_repos.append(repo_name)
                            if not found_js and lang_data.get("JavaScript", 0) > 0:
                                found_js = True
                                js_repos.append(repo_name)
                        elif lang_resp.status_code == 403 and "rate limit" in lang_resp.text.lower():
                            return GitHubVerificationResult(
                                status="API_RATE_LIMITED",
                                username=username,
                                evidence_summary=f"Rate limit hit while inspecting repository {repo_name}",
                                repositories_checked=repos_checked_count,
                                error_code="RATE_LIMIT",
                            )
                    except Exception:
                        pass

                # If all 3 have been confirmed across candidate repos, stop early
                if found_playwright and found_ts and found_js:
                    break

            langs_list: List[str] = []
            if found_playwright:
                langs_list.append("Playwright")
            if found_ts:
                langs_list.append("TypeScript")
            if found_js:
                langs_list.append("JavaScript")

            if langs_list:
                languages_found_str = ", ".join(langs_list)
                evidence_str = f"QA Automation found: {languages_found_str}"
                user_data = user_resp.json() if user_resp.status_code == 200 else {}
                git_score = calculate_qa_git_score(user_data, repos, languages_found=languages_found_str)
                logger.info("Candidate %s: QA_AUTOMATION_DETECTED (%s, GitScore: %s/10)", username, evidence_str, git_score)
                return GitHubVerificationResult(
                    status="QA_AUTOMATION_DETECTED",
                    username=username,
                    evidence_summary=evidence_str,
                    repositories_checked=repos_checked_count,
                    languages_found=languages_found_str,
                    git_score=git_score,
                )'''

new_qa_block = '''        if tech in ("qa_automation", "qa"):
            found_playwright = False
            found_cypress = False
            found_webdriverio = False
            found_ts = False
            found_js = False
            playwright_repos: List[str] = []
            cypress_repos: List[str] = []
            webdriverio_repos: List[str] = []
            ts_repos: List[str] = []
            js_repos: List[str] = []
            repos_checked_count = 0

            for repo in repos:
                repo_name = repo.get("name", "")
                repo_name_lower = repo_name.lower()
                repo_desc_lower = (repo.get("description") or "").lower()
                primary_lang = (repo.get("language") or "").strip().lower()
                topics = [t.lower() for t in (repo.get("topics", []) or [])]
                repos_checked_count += 1

                # 1. Playwright check
                if not found_playwright:
                    if (
                        "playwright" in repo_name_lower
                        or "playwright" in repo_desc_lower
                        or any("playwright" in t for t in topics)
                    ):
                        found_playwright = True
                        playwright_repos.append(repo_name)

                # 2. Cypress check
                if not found_cypress:
                    if (
                        "cypress" in repo_name_lower
                        or "cypress" in repo_desc_lower
                        or any("cypress" in t for t in topics)
                    ):
                        found_cypress = True
                        cypress_repos.append(repo_name)

                # 3. WebdriverIO check
                if not found_webdriverio:
                    if (
                        "webdriverio" in repo_name_lower
                        or "wdio" in repo_name_lower
                        or "webdriverio" in repo_desc_lower
                        or "wdio" in repo_desc_lower
                        or any(t in ["webdriverio", "wdio", "webdriver-io"] for t in topics)
                    ):
                        found_webdriverio = True
                        webdriverio_repos.append(repo_name)

                # 4. TypeScript (TS) check
                if not found_ts:
                    if primary_lang == "typescript" or any(t in ["typescript", "ts"] for t in topics):
                        found_ts = True
                        ts_repos.append(repo_name)

                # 5. JavaScript (JS) check
                if not found_js:
                    if primary_lang in ["javascript", "node", "nodejs"] or any(
                        t in ["javascript", "js", "node", "nodejs"] for t in topics
                    ):
                        found_js = True
                        js_repos.append(repo_name)

                # Query languages API if TS or JS not yet confirmed
                if (not found_ts or not found_js) and repo.get("languages_url"):
                    try:
                        lang_resp = await client.get(repo.get("languages_url"), headers=headers)
                        if lang_resp.status_code == 200:
                            lang_data = lang_resp.json()
                            if not found_ts and lang_data.get("TypeScript", 0) > 0:
                                found_ts = True
                                ts_repos.append(repo_name)
                            if not found_js and lang_data.get("JavaScript", 0) > 0:
                                found_js = True
                                js_repos.append(repo_name)
                        elif lang_resp.status_code == 403 and "rate limit" in lang_resp.text.lower():
                            return GitHubVerificationResult(
                                status="API_RATE_LIMITED",
                                username=username,
                                evidence_summary=f"Rate limit hit while inspecting repository {repo_name}",
                                repositories_checked=repos_checked_count,
                                error_code="RATE_LIMIT",
                            )
                    except Exception:
                        pass

                # If all frameworks and languages have been found, stop early
                if found_playwright and found_cypress and found_webdriverio and found_ts and found_js:
                    break

            langs_list: List[str] = []
            if found_playwright:
                langs_list.append("Playwright")
            if found_cypress:
                langs_list.append("Cypress")
            if found_webdriverio:
                langs_list.append("WebdriverIO")
            if found_ts:
                langs_list.append("TypeScript")
            if found_js:
                langs_list.append("JavaScript")

            if langs_list:
                languages_found_str = ", ".join(langs_list)
                evidence_str = f"QA Automation found: {languages_found_str}"
                user_data = user_resp.json() if user_resp.status_code == 200 else {}
                git_score = calculate_qa_git_score(user_data, repos, languages_found=languages_found_str, technology="qa_automation")
                logger.info("Candidate %s: QA_AUTOMATION_DETECTED (%s, GitScore: %s/10)", username, evidence_str, git_score)
                return GitHubVerificationResult(
                    status="QA_AUTOMATION_DETECTED",
                    username=username,
                    evidence_summary=evidence_str,
                    repositories_checked=repos_checked_count,
                    languages_found=languages_found_str,
                    git_score=git_score,
                )'''

assert old_qa_block in content, "old_qa_block not found"
content = content.replace(old_qa_block, new_qa_block, 1)

file_path.write_text(content, encoding="utf-8", newline="\r\n")
print("Successfully enhanced QA keywords for Playwright, Cypress, and WebdriverIO!")
