import random

async def human_type(page, selector, text):
    await page.click(selector)
    await page.fill(selector, "")  # clear first

    for char in text:
        await page.type(selector, char, delay=random.randint(50, 120))