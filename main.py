from fastapi import FastAPI, Query
from playwright.async_api import async_playwright

app = FastAPI()

@app.get("/resolve")
async def resolve(url: str = Query(...)):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
        page = await context.new_page()

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        final_url = page.url
        await browser.close()

        return {
            "dirty": url,
            "clean": final_url
        }
