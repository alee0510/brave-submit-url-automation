from playwright.async_api import TimeoutError as PlaywrightTimeoutError

async def detect_success(page):
    try:
        await page.wait_for_selector("div.info:has-text('Success')", timeout=5000)
        return True
    except PlaywrightTimeoutError:
        return False