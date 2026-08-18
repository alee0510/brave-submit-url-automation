import asyncio
import random
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from config import BASE_URL, TIMEOUT, COOLDOWN_MIN, COOLDOWN_MAX


class AsyncWorker:
    def __init__(self, logger):
        self.logger = logger

    async def run(self, queue):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)

            # Persistent context helps reduce repeated captcha
            context = await browser.new_context()
            page = await context.new_page()

            for url in queue:
                success = await self.process(page, url)
                yield url, success

                cooldown = random.randint(COOLDOWN_MIN, COOLDOWN_MAX)
                self.logger.info(f"Cooldown {cooldown}s...")
                await asyncio.sleep(cooldown)

            await browser.close()

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