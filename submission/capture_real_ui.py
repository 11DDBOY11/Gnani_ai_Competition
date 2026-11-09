import asyncio
import os
import subprocess
import time
import socket
from playwright.async_api import async_playwright

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

os.makedirs("docs/images", exist_ok=True)

async def capture():
    port = find_free_port()
    # Start uvicorn
    proc = subprocess.Popen(
        ["python", "-m", "uvicorn", "app.server:app", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)  # wait for uvicorn to boot
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(channel="msedge")
            page = await browser.new_page(viewport={"width": 1280, "height": 900})
            
            # 1. Landing Page
            print("Capturing Landing Page...")
            await page.goto(f"http://localhost:{port}/", wait_until="networkidle")
            await page.screenshot(path="docs/images/landing_page.png")
            
            # 2. Ask Page
            print("Capturing Ask Page...")
            await page.goto(f"http://localhost:{port}/ask", wait_until="networkidle")
            await page.screenshot(path="docs/images/ask_page.png")
            
            # 3. Ask Page Mobile View
            print("Capturing Ask Mobile...")
            await page.set_viewport_size({"width": 420, "height": 860})
            await page.screenshot(path="docs/images/ask_page_mobile.png")
            
            # 4. Simulator Page Desktop View
            print("Capturing Sim Page...")
            await page.set_viewport_size({"width": 1280, "height": 900})
            await page.goto(f"http://localhost:{port}/sim", wait_until="networkidle")
            await page.screenshot(path="docs/images/sim_page.png")
            
            await browser.close()
            print("All screenshots successfully captured with full CSS styling!")
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    asyncio.run(capture())
