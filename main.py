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

    # Попытка через браузер
    playwright = None
    browser = None
    
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        
        page = await browser.new_page()
        
        # Собираем все URL куда переходит страница
        urls = [url]
        final_url = url
        
        # Отслеживаем навигацию (это главное для JS редиректов!)
        def on_frame_navigated(frame):
            nonlocal final_url
            if frame == page.main_frame:
                final_url = frame.url
                urls.append(frame.url)
                print(f"Navigated to: {frame.url}")
        
        page.on("framenavigated", on_frame_navigated)
        
        async def handle_response(response):
            if response.status >= 300 and response.status < 400:
                print(f"Redirect: {response.status} -> {response.url}")
        
        page.on("response", handle_response)
        
        # Переходим и ждем
        try:
            print(f"Loading: {url}")
            await page.goto(url, wait_until="networkidle", timeout=20000)
            print(f"Page loaded, current URL: {page.url}")
        except Exception as e:
            print(f"Goto error: {e}, current URL: {page.url}")
        
        # Еще подождем для JS редиректов - увеличиваем до 5 секунд
        print("Waiting for JS redirects...")
        await asyncio.sleep(5)
        
        # Финальный URL
        final_url = page.url
        print(f"Final URL: {final_url}")
        
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