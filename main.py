# main.py
from fastapi import FastAPI, Query
from playwright.async_api import async_playwright
import asyncio

app = FastAPI()

@app.get("/resolve")
async def resolve(url: str = Query(...)):
    browser = None
    try:
        playwright = await async_playwright().start()
        
        # Запускаем браузер
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )
        
        # Создаем контекст и страницу
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120 Safari/537.36"
            )
        )
        page = await context.new_page()

        final_url = url

        # Отслеживаем навигацию
        async def handle_navigation(frame):
            nonlocal final_url
            final_url = frame.url

        page.on("framenavigated", lambda frame: asyncio.create_task(handle_navigation(frame)))

        # Переходим по ссылке
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            # Игнорируем таймауты навигации
            print(f"Navigation warning: {e}")

        # Ждем JS редиректы
        await page.wait_for_timeout(3000)
        
        # Получаем финальный URL
        final_url = page.url

        # Закрываем всё
        await context.close()
        await browser.close()
        await playwright.stop()

        return {
            "dirty": url,
            "clean": final_url
        }
        
    except Exception as e:
        if browser:
            try:
                await browser.close()
            except:
                pass
        return {
            "dirty": url,
            "clean": url,
            "error": str(e)
        }