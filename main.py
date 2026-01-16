# main.py
from fastapi import FastAPI, Query
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import httpx
import asyncio
import os

app = FastAPI()

# Глобальный Playwright для переиспользования
_playwright = None
_browser = None

async def get_browser():
    global _playwright, _browser
    
    if _browser is None or not _browser.is_connected():
        if _playwright is None:
            _playwright = await async_playwright().start()
        
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer",
                "--disable-extensions"
            ]
        )
    
    return _browser

@app.get("/")
async def root():
    return {"status": "ok", "message": "Proxy Redirect Resolver API"}

@app.get("/resolve")
async def resolve(url: str = Query(...)):
    # Шаг 1: HTTP попытка
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, 
            timeout=5.0
        ) as client:
            response = await client.head(url, follow_redirects=True)
            intermediate_url = str(response.url)
            
            if intermediate_url != url:
                return {
                    "dirty": url,
                    "clean": intermediate_url,
                    "method": "http"
                }
    except Exception as e:
        print(f"HTTP failed: {e}")
        intermediate_url = url

    # Шаг 2: Браузер
    context = None
    try:
        browser = await get_browser()
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            ignore_https_errors=True
        )
        
        page = await context.new_page()
        
        # Блокируем тяжелые ресурсы
        await page.route("**/*", lambda route: (
            route.abort() if route.request.resource_type in ["image", "stylesheet", "font", "media"]
            else route.continue_()
        ))
        
        try:
            await page.goto(
                intermediate_url, 
                wait_until="domcontentloaded",
                timeout=10000
            )
            await asyncio.sleep(1.5)
            
            final_url = page.url
        except PlaywrightTimeout:
            final_url = page.url if page.url != "about:blank" else intermediate_url
        
        await context.close()

        return {
            "dirty": url,
            "clean": final_url,
            "method": "browser"
        }
        
    except Exception as e:
        if context:
            try:
                await context.close()
            except:
                pass
        
        return {
            "dirty": url,
            "clean": intermediate_url,
            "error": str(e),
            "method": "fallback"
        }

@app.on_event("shutdown")
async def shutdown_event():
    global _browser, _playwright
    if _browser:
        await _browser.close()
    if _playwright:
        await _playwright.stop()

# Для запуска напрямую
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)