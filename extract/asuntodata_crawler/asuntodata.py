import asyncio
import sys
import csv
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from fake_useragent import UserAgent
from playwright_stealth import stealth_async

sys.path.append(str(Path(__file__).resolve().parents[2]))


import requests


# Fetch finnish post codes
def fetch_post_codes():
    url = "https://raw.githubusercontent.com/theikkila/postinumerot/refs/heads/master/postcodes.json"
    response = requests.get(url)
    response.raise_for_status()  # will raise an exception for HTTP errors
    data = response.json()
    post_codes = []
    for item in data:
        post_codes.append(item['postcode'])
    post_codes.sort()
    return post_codes


FIELD_NAMES = [
    "kaupunginosa", "huoneisto", "talotyyppi", "neliot", "velaton_hinta",
    "neliohinta", "rakennusvuosi", "kerros", "hissi", "kunto", "tontti", "energialuokka"
]


async def crawl_etuovi():
    from pathlib import Path

    # Store collected rows here
    all_rows = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ua = UserAgent()
        context = await browser.new_context(user_agent=ua.random)
        page = await context.new_page()

        await stealth_async(page)
        await page.goto("https://asuntojen.hintatiedot.fi/haku/")

        post_codes = fetch_post_codes()
        for post_code in post_codes:
            print(f"\n📍 Fetching data for postcode: {post_code}")
            await page.get_by_role("textbox", name="Postinumero").click()
            await page.get_by_role("textbox", name="Postinumero").fill(post_code)
            await page.get_by_role("button", name="Haku").click()

            empty_page = await page.query_selector("text=Tuloksia on vähemmän kuin")
            if empty_page:
                print("⚠️ Too few results. Skipping.")
                continue

            await page.wait_for_selector("#mainTable")

            while True:
                main_table = await page.query_selector("#mainTable")
                if main_table:
                    tbodys = await main_table.query_selector_all("tbody")
                    for tbody in tbodys:
                        trs = await tbody.query_selector_all("tr")
                        if len(trs) > 2:
                            apartment_type = (await trs[0].inner_text()).strip()
                            for tr in trs[1:]:
                                tds = await tr.query_selector_all("td")
                                if len(tds) == len(FIELD_NAMES):
                                    row_data = {
                                        name: (await td.inner_text()).strip()
                                        for name, td in zip(FIELD_NAMES, tds)
                                    }
                                    row_data["apartment_type"] = apartment_type
                                    row_data["postcode"] = post_code
                                    all_rows.append(row_data)

                submit_button = page.locator('input[type="submit"][value="seuraava sivu »"]').first
                if await submit_button.count() > 0 and await submit_button.is_enabled():
                    print("➡️ Next page...")
                    await submit_button.click()
                    await page.wait_for_selector("#mainTable", timeout=5000)
                else:
                    print("✅ Done with this postcode.")
                    break

        await browser.close()

    # ✅ Save to CSV
    output_dir = Path(r"\app\data\asuntodata")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "asuntodata.csv"

    fieldnames = FIELD_NAMES + ["apartment_type", "postcode"]
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n💾 Data saved to: {output_file}")




if __name__ == "__main__":
    asyncio.run(crawl_etuovi())


