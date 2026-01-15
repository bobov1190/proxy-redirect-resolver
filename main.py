# main.py
from fastapi import FastAPI, Query
from playwright.async_api import async_playwright
import asyncio

app = FastAPI()

@app.get("/resolve")
async def resolve(url: str = Query(...)):
    playwright = None
    browser = None
    context = None
    
    try:
        playwright = await async_playwright().start()
        
        # Запускаем браузер
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )
        
        # Создаем контекст и страницу
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        
        page = await context.new_page()
        
        # Увеличиваем таймаут и используем более мягкие условия ожидания
        final_url = url
        
        try:
            # Пробуем загрузить страницу с более мягким wait_until
            response = await page.goto(
                url, 
                wait_until="domcontentloaded",  # Вместо networkidle
                timeout=15000
            )
            
            # Ждем дополнительные редиректы
            await page.wait_for_timeout(2000)
            
            # Получаем финальный URL
            final_url = page.url
            
        except Exception as nav_error:
            # Если навигация не удалась, пробуем получить текущий URL
            print(f"Navigation error: {nav_error}")
            try:
                final_url = page.url if page.url != "about:blank" else url
            except:
                final_url = url

        # Закрываем всё
        await page.close()
        await context.close()
        await browser.close()
        await playwright.stop()

        return {
            "dirty": url,
            "clean": final_url
        }
        
    except Exception as e:
        # Cleanup
        try:
            if context:
                await context.close()
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
        except:
            pass
            
        return {
            "dirty": url,
            "clean": url,
            "error": str(e)
        }