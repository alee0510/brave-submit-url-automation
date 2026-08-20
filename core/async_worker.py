import os
import asyncio
import random
import time
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from config import (
    BASE_URL, PROFILE_DIR, ERRORS_DIR, LOGS_CSV,
    COOLDOWN_MIN, COOLDOWN_MAX,
    BATCH_SIZE, BATCH_PAUSE_MIN, BATCH_PAUSE_MAX,
    CAPTCHA_AUTO_TIMEOUT_MS, SELECTOR_TIMEOUT_MS,
)
from core.human_type import human_type
from core.logger import log_to_file

class AsyncWorker:
    def __init__(self, logger):
        self.logger = logger
        # Lightweight PoW visibility — not persisted, just logged at run end
        self.pow_stats = {"auto_resolved": 0, "timed_out": 0}

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
                    success, detail = await self.process(page, url)
                    yield url, success, detail

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

                    if (i + 1) % BATCH_SIZE == 0 and (i + 1) < len(queue):
                        batch_pause = random.uniform(BATCH_PAUSE_MIN, BATCH_PAUSE_MAX)
                        self.logger.info(f"[BATCH PAUSE] Processed {i + 1} URLs, pausing {batch_pause:.2f}s")
                        await asyncio.sleep(batch_pause)
            finally:
                self.logger.info(
                    f"[POW SUMMARY] auto_resolved={self.pow_stats['auto_resolved']} "
                    f"timed_out={self.pow_stats['timed_out']}"
                )
                await context.close()

    async def process(self, page, url):
        try:
            self.logger.info(f"[START] Processing URL: {url}")

            self.logger.info("[STEP 1] Navigating to Brave submit page...")
            await page.goto(BASE_URL, wait_until="domcontentloaded")
            self.logger.info(f"[STEP 1 DONE] Current URL: {page.url}")

            self.logger.info("[STEP 2] Waiting for #url input...")
            await page.wait_for_selector("#url", timeout=SELECTOR_TIMEOUT_MS)
            self.logger.info("[STEP 2 DONE] Input detected")

            self.logger.info("[STEP 3] Typing URL...")
            await human_type(page, "#url", url)
            self.logger.info("[STEP 3 DONE] Typing complete")

            delay = random.uniform(0.5, 1.5)
            self.logger.info(f"[STEP 4] Human delay {delay:.2f}s")
            await asyncio.sleep(delay)

            self.logger.info("[STEP 5] Waiting for button enabled (PoW captcha)...")
            resolved = await self.wait_for_button_enabled(page)
            if not resolved:
                detail = "PoW captcha timeout"
                self.logger.warning(f"[FAILED] {detail} | {url}")
                log_to_file(LOGS_CSV, url, "failed", 1, detail)
                return False, detail
            self.logger.info("[STEP 5 DONE] Button enabled")

            self.logger.info("[STEP 6] Clicking submit...")
            await page.click("button[name='captcha-button']")
            self.logger.info("[STEP 6 DONE] Click executed")

            self.logger.info("[STEP 7] Waiting for success signal...")
            success, detail = await self.wait_for_success(page)

            if success:
                self.logger.info(f"[SUCCESS] {url}")
                return True, None
            else:
                self.logger.warning(f"[FAILED] {detail or 'No success signal'} | {url}")
                log_to_file(LOGS_CSV, url, "failed", 1, detail)
                return False, detail

        except Exception as e:
            detail = str(e)
            self.logger.error(f"[ERROR] {url} | {type(e).__name__} | {detail}")
            log_to_file(LOGS_CSV, url, "error", 1, detail)
            return False, detail

    async def wait_for_button_enabled(self, page, timeout=CAPTCHA_AUTO_TIMEOUT_MS):
        """
        Wait for the PoW challenge to resolve automatically.
        Fully unattended — returns True if resolved, False on timeout.
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
            self.pow_stats["auto_resolved"] += 1
            return True
        except PlaywrightTimeoutError:
            self.pow_stats["timed_out"] += 1
            self.logger.warning(f"[TIMEOUT] PoW did not resolve within {timeout / 1000:.0f}s")
            await self.debug_snapshot(page, "pow_timeout")
            return False

    async def wait_for_success(self, page):
        try:
            await page.wait_for_selector(
                "div.info.error, div.info:has-text('Success')",
                timeout=SELECTOR_TIMEOUT_MS
            )
        except PlaywrightTimeoutError:
            await self.debug_snapshot(page, "timeout")
            try:
                btn_text = await page.text_content("button[name='captcha-button']")
                if btn_text and "submitted" in btn_text.lower():
                    return True, None
            except Exception:
                pass
            return False, "Timed out waiting for a success/error signal"

        error_el = await page.query_selector("div.info.error")
        if error_el:
            detail = await self._extract_message(error_el)
            self.logger.warning(f"[ERROR SIGNAL] {detail}")
            await self.debug_snapshot(page, "error")
            return False, detail

        return True, None

    async def _extract_message(self, element):
        try:
            detail_el = await element.query_selector(".t-tertiary")
            text = await (detail_el.inner_text() if detail_el else element.inner_text())
            return text.strip()
        except Exception:
            return "Unknown error (could not read message)"

    async def debug_snapshot(self, page, label="debug"):
        try:
            os.makedirs(ERRORS_DIR, exist_ok=True)
            path = os.path.join(ERRORS_DIR, f"debug_{label}_{int(time.time())}.html")
            content = await page.content()
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.logger.info(f"[SNAPSHOT] Saved DOM to {path}")
        except Exception as e:
            self.logger.warning(f"[SNAPSHOT ERROR] {e}")