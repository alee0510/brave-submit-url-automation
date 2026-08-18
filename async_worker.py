import os
import asyncio
import random
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from config import BASE_URL, TIMEOUT, COOLDOWN_MIN, COOLDOWN_MAX, PROFILE_DIR

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
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
            )

            page = context.pages[0] if context.pages else await context.new_page()

            for i, url in enumerate(queue):
                success = await self.process(page, url)
                yield url, success

                if success:
                    cooldown = random.uniform(COOLDOWN_MAX, COOLDOWN_MAX)
                else:
                    cooldown = random.uniform(COOLDOWN_MIN * 2.0, COOLDOWN_MAX * 3.0)

                self.logger.info(f"Cooldown {cooldown}s...")
                await asyncio.sleep(cooldown)

            await context.close()

    async def process(self, page, url):
        try:
            self.logger.info(f"Submitting: {url}")

            await page.goto(BASE_URL, timeout=TIMEOUT)

            # 1. Fill input (stable selector)
            await page.fill("#url", url)

            # 2. Wait for submit button to be enabled
            self.logger.info("Waiting for captcha / button enable...")
            await self.wait_for_button_enabled(page)

            # 3. Click submit
            await page.click("button[name='captcha-button']")
            self.logger.info("Submit clicked")

            # 4. Detect success
            success = await self.wait_for_success(page)

            if success:
                self.logger.info("✅ Success detected")
                return True
            else:
                self.logger.warning("❌ Success not detected")
                return False

        except Exception as e:
            self.logger.error(f"Error: {e}")
            return False

    async def wait_for_button_enabled(self, page, timeout=120000):
        """
        Wait until captcha is solved and button becomes enabled.
        Fallback to manual ENTER if needed.
        """
        try:
            await page.wait_for_function(
                """() => {
                    const btn = document.querySelector("button[name='captcha-button']");
                    return btn && !btn.disabled;
                }""",
                timeout=timeout
            )
        except PlaywrightTimeoutError:
            self.logger.warning("⚠️ Button still disabled. Solve captcha manually.")
            input("👉 Solve captcha, then press ENTER...")

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
            pass

        # Fallback: check button text (Submitted)
        try:
            btn_text = await page.text_content("button[name='captcha-button']")
            if btn_text and "submitted" in btn_text.lower():
                return True
        except:
            pass

        return False