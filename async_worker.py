import os
import asyncio
import random
import time
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from config import BASE_URL, COOLDOWN_MIN, COOLDOWN_MAX, PROFILE_DIR, FAILED_LOG
from human_type import human_type
from logger import log_to_file

class AsyncWorker:
    def __init__(self, logger):
        self.logger = logger

    async def run(self, queue):
        os.makedirs(PROFILE_DIR, exist_ok=True)

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=PROFILE_DIR,
                headless=False,
                channel="chrome",
                args=["--start-maximized", "--disable-blink-features=AutomationControlled", "--enable-sandbox"]
            )

            try:
                failure_streak = 0
                page = context.pages[0] if context.pages else await context.new_page()

                for i, url in enumerate(queue):
                    success = await self.process(page, url)
                    yield url, success

                    if success:
                        failure_streak = 0
                        cooldown = random.uniform(COOLDOWN_MIN, COOLDOWN_MAX)
                    else:
                        failure_streak += 1
                        cooldown = min(60, random.uniform(COOLDOWN_MIN * 2.0, COOLDOWN_MAX * 2.0) * (2 ** failure_streak))

                    self.logger.info(
                        f"[BACKOFF] success={success} | streak={failure_streak} | sleep={cooldown:.2f}s"
                    )
                    await asyncio.sleep(cooldown)
            finally:
                await context.close()

    async def process(self, page, url):
        try:
            self.logger.info(f"[START] Processing URL: {url}")

            # STEP 1: Navigate
            self.logger.info("[STEP 1] Navigating to Brave submit page...")
            await page.goto(BASE_URL, wait_until="domcontentloaded")
            current_url = page.url
            self.logger.info(f"[STEP 1 DONE] Current URL: {current_url}")

            # STEP 2: Wait for input
            self.logger.info("[STEP 2] Waiting for #url input...")
            await page.wait_for_selector("#url", timeout=10000)
            self.logger.info("[STEP 2 DONE] Input detected")

            # STEP 3: Human typing
            self.logger.info("[STEP 3] Typing URL...")
            await human_type(page, "#url", url)
            self.logger.info("[STEP 3 DONE] Typing complete")

            # STEP 4: Pre-submit delay
            delay = random.uniform(0.5, 1.5)
            self.logger.info(f"[STEP 4] Human delay {delay:.2f}s")
            await asyncio.sleep(delay)

            # STEP 5: Wait for captcha/button
            self.logger.info("[STEP 5] Waiting for button enabled (captcha)...")
            await self.wait_for_button_enabled(page)
            self.logger.info("[STEP 5 DONE] Button enabled")

            # STEP 6: Click submit
            self.logger.info("[STEP 6] Clicking submit...")
            await page.click("button[name='captcha-button']")
            self.logger.info("[STEP 6 DONE] Click executed")

            # STEP 7: Wait for success
            self.logger.info("[STEP 7] Waiting for success signal...")
            success = await self.wait_for_success(page)

            if success:
                self.logger.info(f"[SUCCESS] {url}")
                return True
            else:
                self.logger.warning(f"[FAILED] No success signal for {url}")
                return False

        except Exception as e:
            self.logger.error(f"[ERROR] {url} | {type(e).__name__} | {e}")
            log_to_file(FAILED_LOG, url, "error", 1, str(e))
            return False

    async def wait_for_button_enabled(self, page, timeout=120000):
        """
        Wait until captcha is solved and button becomes enabled.
        Fallback to manual ENTER if needed.
        """
        try:
            self.logger.info("[WAIT] Monitoring button state...")
            await page.wait_for_function(
                """() => {
                    const btn = document.querySelector("button[name='captcha-button']");
                    return btn && !btn.disabled;
                }""",
                timeout=timeout
            )
        except PlaywrightTimeoutError:
            self.logger.warning("[TIMEOUT] ⚠️ Button still disabled (captcha likely present)")
             # 🔍 EXTRA DEBUG: check button state
            try:
                disabled = await page.eval_on_selector(
                    "button[name='captcha-button']",
                    "el => el.disabled"
                )
                self.logger.warning(f"[DEBUG] Button disabled = {disabled}")
            except:
                self.logger.warning("[DEBUG] Could not inspect button")

            await asyncio.to_thread(input, "👉 Solve captcha, then press ENTER...")

    async def wait_for_success(self, page):
        """
        Detect success using multiple signals
        """
        try:
            await page.wait_for_selector(
                "div.info:has-text('Success')",
                timeout=10000
            )
            return True
        except PlaywrightTimeoutError:
            await self.debug_snapshot(page, "error")

        # Fallback: check button text (Submitted)
        try:
            btn_text = await page.text_content("button[name='captcha-button']")
            if btn_text and "submitted" in btn_text.lower():
                return True
        except:
            await self.debug_snapshot(page, "error")

        return False

    async def debug_snapshot(self, page, label="debug"):
        try:
            path = f"debug_{label}_{int(time.time())}.html"
            content = await page.content()

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            self.logger.info(f"[SNAPSHOT] Saved DOM to {path}")
        except Exception as e:
            self.logger.warning(f"[SNAPSHOT ERROR] {e}")