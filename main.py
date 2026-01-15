# main.py
from fastapi import FastAPI, Query
from playwright.async_api import async_playwright
import httpx
import asyncio

app = FastAPI()

@app.get("/resolve")
async def resolve(url: str = Query(...)):
    # Сначала пробуем простой HTTP редирект
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.get(url)
            intermediate_url = str(response.url)
            
            # Если это простой HTTP редирект - возвращаем
            if intermediate_url != url and "javascript" not in intermediate_url.lower():
                return {
                    "dirty": url,
                    "clean": intermediate_url,
                    "method": "http"
                }
    except Exception as e:
        print(f"HTTP redirect failed: {e}")
        intermediate_url = url

    # Если HTTP не помог или есть JS редирект - используем браузер
    playwright = None
    browser = None
    
    try:
        playwright = await async_playwright().start()
        
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            ignore_https_errors=True
        )
        
        page = await context.new_page()
        
        # Загружаем страницу
        await page.goto(intermediate_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)
        
        final_url = page.url
        
        await context.close()
        await browser.close()
        await playwright.stop()

        return {
            "dirty": url,
            "clean": final_url,
            "method": "browser"
        }
        
    except Exception as e:
        try:
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
        except:
            pass
            
        return {
            "dirty": url,
            "clean": intermediate_url if intermediate_url != url else url,
            "error": str(e),
            "method": "fallback"
        }