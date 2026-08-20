import random
from config import FAST_MODE

async def human_type(page, selector, text):
    await page.click(selector)
    await page.fill(selector, "")  # clear first

    if FAST_MODE:
        await page.type(selector, text)
        return

    for char in text:
        await page.type(selector, char, delay=random.randint(50, 120))