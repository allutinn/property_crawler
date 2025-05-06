import asyncio
import os
import re
import json
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from fake_useragent import UserAgent
from playwright_stealth import stealth_async

sys.path.append(str(Path(__file__).resolve().parents[2]))
from extract.redis.client import add_to_queue  # type: ignore

def update_cache(data, filepath="url_store.json"):
    store = {}
    path = Path(filepath)

    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            store = json.load(f)

    updated_rows = {'new': [], 'modified': [], 'exists': []}

    for item in data:
        id = item.get("ad_id")
        ts = item.get("published_or_updated")

        if not id or not ts:
            continue

        if id not in store:
            store[id] = {"timestamp": ts, "row_type": "new"}
            updated_rows['new'].append(id)
        elif store[id]["timestamp"] != ts:
            store[id] = {"timestamp": ts, "row_type": "modified"}
            updated_rows['modified'].append(id)
        else:
            store[id]["row_type"] = "exists"
            updated_rows['exists'].append(id)

    with path.open("w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)

    return updated_rows


async def crawl_etuovi(last_page: int | None = None):
    env_last_page = os.getenv("ETUOVI_LAST_PAGE")
    if last_page is None and env_last_page and env_last_page.isdigit():
        last_page = int(env_last_page)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=500)
        ua = UserAgent()
        context = await browser.new_context(user_agent=ua.random)
        page = await context.new_page()

        await stealth_async(page)

        await page.goto("https://www.etuovi.com/")

        try:
            await page.frame_locator("iframe[title=\"SP Consent Message\"]").get_by_label("Hyv\u00e4ksy").click()
        except PlaywrightTimeout:
            print("(i) Consent popup not found or already accepted.")

        search_button_pattern = re.compile(r"Hae\s*\([^)]*\)")
        await page.get_by_role("button", name=search_button_pattern).click()
        await page.get_by_text("Uudet ja nostetut ensin").click()
        await page.get_by_role("option", name="Uusimmat ensin (ilmoitettu)").click()

        only_existing_streak = 0

        while True:
            await page.reload()

            if 'sivu=' in page.url:
                pagination_number = int(page.url.split('sivu=')[-1])
                if last_page and pagination_number > last_page:
                    break

            await page.wait_for_function("""
                () => {
                    const s = window.__INITIAL_STATE__;
                    return s?.announcementSearch?.searchResults?.announcements?.length > 0;
                }
            """, timeout=10000)

            announcements_id_and_updated = await page.evaluate("""
                () => window.__INITIAL_STATE__
                    ?.announcementSearch
                    ?.searchResults
                    ?.announcements
                    ?.map(a => ({
                        ad_id: a.friendlyId,
                        published_or_updated: a.publishedOrUpdatedAt
                    }))
            """)

            updated_rows = update_cache(announcements_id_and_updated)

            new_rows = [(f'http://etuovi.com/kohde/{id}', 'new') for id in updated_rows['new']]
            modified_rows = [(f'http://etuovi.com/kohde/{id}', 'modified') for id in updated_rows['modified']]
            for url, row_type in new_rows + modified_rows:
                add_to_queue(link=url, row_type=row_type)

            formatted_updates = [f'{key} : {len(val)}' for key,val in updated_rows.items()]
            print(f'Updated cache from page: {page.url} --- {formatted_updates}')

            if len(updated_rows['new']) > 0 or len(updated_rows['modified']) > 0:
                only_existing_streak = 0
            else:
                only_existing_streak += 1
                if not last_page and only_existing_streak >= 2:
                    print("Two pages in a row had only existing announcements. Stopping.")
                    break

            next_button = page.get_by_role("button", name="Seuraava sivu")
            await next_button.click()

        await browser.close()


if __name__ == "__main__":
    asyncio.run(crawl_etuovi())
