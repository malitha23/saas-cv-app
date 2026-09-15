import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        print("Navigating to http://localhost:8000/ ...")
        await page.goto("http://localhost:8000/", wait_until="networkidle")
        await asyncio.sleep(2)

        print(f"Console errors on root: {len(console_errors)}")
        for err in console_errors:
            print("  Root Error:", err)

        # Open pricing modal
        await page.evaluate("window.Alpine.discoverUninitializedComponents() || true")
        modal_opened = await page.evaluate("""() => {
            const scope = Alpine.$data(document.querySelector('[x-data]'));
            if (scope) {
                scope.showPricingModal = true;
                return true;
            }
            return false;
        }""")
        print(f"Pricing modal opened: {modal_opened}")
        await asyncio.sleep(1)

        os.makedirs("scratch", exist_ok=True)
        await page.screenshot(path="scratch/pricing_payhere_view.png")
        print("Captured screenshot: scratch/pricing_payhere_view.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
