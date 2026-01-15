# main.py
from fastapi import FastAPI, Query
from playwright.async_api import async_playwright
import asyncio

app = FastAPI()

@app.get("/resolve")
async def resolve(url: str = Query(...)):
    async with async_playwright() as p:
        # Убираем executable_path - Playwright сам найдет браузер
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",  # Важно для Docker
                "--disable-gpu"
            ]
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120 Safari/537.36"
            )
        )
        page = await context.new_page()

        final_url = url

        def on_frame_navigated(frame):
            nonlocal final_url
            final_url = frame.url

        page.on("framenavigated", on_frame_navigated)

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception:
            pass

        await page.wait_for_timeout(3000)
        await browser.close()

        return {
            "dirty": url,
            "clean": final_url
        }