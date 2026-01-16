# main.py
from fastapi import FastAPI, Query
from playwright.async_api import async_playwright
import httpx
import asyncio
import os

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok", "message": "Proxy Redirect Resolver API"}

@app.get("/resolve")
async def resolve(url: str = Query(...)):
    # Попытка через HTTP
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=8.0) as client:
            response = await client.get(url)
            http_url = str(response.url)
            
            if http_url != url:
                return {"dirty": url, "clean": http_url, "method": "http"}
    except:
        pass

    # Попытка через браузер со stealth
    playwright = None
    browser = None
    
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",  # Важно для обхода детекта
            ]
        )
        
        # Создаем контекст с реалистичными параметрами
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York",
            permissions=["geolocation"],
            geolocation={"latitude": 40.7128, "longitude": -74.0060},  # New York
            color_scheme="light",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Sec-Fetch-Dest": "document",
            }
        )
        
        page = await context.new_page()
        
        # Скрываем WebDriver
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Добавляем реалистичные свойства
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Переопределяем chrome object
            window.chrome = {
                runtime: {}
            };
            
            // Переопределяем permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        # Собираем все URL
        urls = [url]
        final_url = url
        
        def on_frame_navigated(frame):
            nonlocal final_url
            if frame == page.main_frame:
                final_url = frame.url
                urls.append(frame.url)
                print(f"Navigated to: {frame.url[:100]}...")
        
        page.on("framenavigated", on_frame_navigated)
        
        # Переходим и ждем
        try:
            print(f"Loading: {url[:100]}...")
            await page.goto(url, wait_until="networkidle", timeout=25000)
            print(f"Page loaded, current URL: {page.url[:100]}...")
        except Exception as e:
            print(f"Goto error: {str(e)[:100]}, current URL: {page.url[:100]}...")
        
        # Ждем дольше для Cloudflare challenge
        print("Waiting for redirects and challenges...")
        await asyncio.sleep(8)  # Cloudflare challenge занимает ~5 секунд
        
        # Финальный URL
        final_url = page.url
        print(f"Final URL: {final_url[:100]}...")
        
        await context.close()
        await browser.close()
        await playwright.stop()
        
        return {"dirty": url, "clean": final_url, "method": "browser", "hops": len(urls)}
        
    except Exception as e:
        if browser:
            try:
                await browser.close()
            except:
                pass
        if playwright:
            try:
                await playwright.stop()
            except:
                pass
        
        return {"dirty": url, "clean": url, "error": str(e), "method": "error"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)