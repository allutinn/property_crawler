from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Tuple

from fake_useragent import UserAgent
from playwright.async_api import (
    Error as PlaywrightError,
    Page,
    TimeoutError as PlaywrightTimeout,
    async_playwright,
)
from playwright_stealth import stealth_async

# ---------------------------------------------------------------------------
# Local package import – abort early if missing
# ---------------------------------------------------------------------------
try:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from extract.redis.client import pop_from_queue, queue_length  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit("❌  Could not import 'extract.redis.client'. Ensure PYTHONPATH is correct.") from exc

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
RAW_BASE_DIR: Path = Path("/app/data/raw")
POLL_INTERVAL: int = 5               # seconds between Redis polls
HEADLESS: bool = True
SLOW_MO: int | None = None           # ms between actions (None = fastest)
DEFAULT_TIMEOUT: int = 10_000        # ms for Playwright waits

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("daily_json_crawler")

# ---------------------------------------------------------------------------
# Runtime state (module‑level singletons)
# ---------------------------------------------------------------------------
_current_day: Optional[str] = None
_ndjson_file: Optional[TextIO] = None

# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _open_ndjson(day: str) -> TextIO:
    """Return an *append* handle for ../data/raw/<day>/<day>.ndjson."""
    day_dir = RAW_BASE_DIR / day
    day_dir.mkdir(parents=True, exist_ok=True)
    return open(day_dir / f"{day}.ndjson", "a", encoding="utf-8")


def _rollover_if_needed(now: datetime) -> None:
    """Close the current file and open a new one if the calendar date changed."""
    global _current_day, _ndjson_file
    day = now.strftime("%Y-%m-%d")
    if day == _current_day:
        return

    if _ndjson_file is not None:
        _ndjson_file.close()
        logger.info("Closed NDJSON file for %s", _current_day)

    _current_day = day
    _ndjson_file = _open_ndjson(day)
    logger.info("Opened NDJSON file for %s", day)


# ---------------------------------------------------------------------------
# Data cleanup
# ---------------------------------------------------------------------------

def _clean_row(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Trim heavy keys & add helper columns (mutates copy, not original)."""
    row = raw.copy()

    # Count images – handles different schema variants gracefully
    img_sorted = None
    if isinstance(row.get("imageIds"), dict):
        img_sorted = row["imageIds"].get("sorted")
    row["number_of_images"] = len(img_sorted) if img_sorted else 0

    # Add crawl timestamp (ISO, seconds granularity)
    row["timestamp_crawled"] = datetime.now().isoformat(timespec="seconds")

    # Drop heavy / irrelevant keys
    for key in ("imageIds", "productEffects", "property.images"):
        row.pop(key, None)

    return row

# ---------------------------------------------------------------------------
# Playwright browser/helpers
# ---------------------------------------------------------------------------

async def _create_browser() -> Tuple[Any, Any, Page]:
    """Return (playwright, browser, page) pre‑configured."""
    playwright = await async_playwright().start()
    ua_fallback = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    try:
        user_agent = UserAgent().random  # type: ignore[assignment]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to obtain random UA – using fallback (%s)", exc)
        user_agent = ua_fallback

    browser = await playwright.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO)
    context = await browser.new_context(user_agent=user_agent)
    page = await context.new_page()
    await stealth_async(page)
    return playwright, browser, page


async def _ensure_cookie_consent(page: Page) -> None:
    try:
        frame = page.frame_locator("iframe[title='SP Consent Message']")
        await frame.get_by_label("Hyväksy").click(timeout=1500)
        logger.debug("Cookie consent accepted.")
    except PlaywrightTimeout:
        logger.debug("Consent iframe not present (likely already accepted).")
    except PlaywrightError as exc:
        logger.warning("Unexpected cookie‑consent error: %s", exc)


async def _fetch_item_payload(page: Page, url: str) -> Optional[Dict[str, Any]]:
    """Navigate to *url* and return Redux item payload, or None on failure."""
    try:
        resp = await page.goto(url, timeout=DEFAULT_TIMEOUT, wait_until="domcontentloaded")
        if not resp or resp.status != 200:
            logger.error("HTTP %s for %s", resp.status if resp else "n/a", url)
            return None

        await _ensure_cookie_consent(page)
        await page.wait_for_function("window.__INITIAL_STATE__?.item?.data", timeout=DEFAULT_TIMEOUT)
        payload: Dict[str, Any] = await page.evaluate("window.__INITIAL_STATE__.item.data")
        return payload
    except PlaywrightTimeout:
        logger.error("Timeout while loading %s", url)
    except PlaywrightError as exc:
        logger.error("Playwright error for %s: %s", url, exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unhandled exception for %s: %s", url, exc)
    return None

# ---------------------------------------------------------------------------
# Task processing
# ---------------------------------------------------------------------------

async def _process_task(page: Page, task: Dict[str, Any]) -> None:
    url = task.get("url")
    if not url:
        logger.warning("Malformed task: %s", task)
        return

    logger.info("Processing %s", url)
    payload = await _fetch_item_payload(page, url)
    if payload is None:
        return  # error already logged

    row = _clean_row(payload)
    now = datetime.now()
    _rollover_if_needed(now)

    assert _ndjson_file is not None, "NDJSON file handle should be open"
    _ndjson_file.write(json.dumps(row, ensure_ascii=False) + "\n")
    _ndjson_file.flush()
    logger.info("Appended row to %s/%s.ndjson", now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d"))

# ---------------------------------------------------------------------------
# Main event loop
# ---------------------------------------------------------------------------

async def _event_loop() -> None:
    playwright, browser, page = await _create_browser()
    logger.info("Browser started (headless=%s).", HEADLESS)

    try:
        while True:
            try:
                logger.info("Items in queue: %d", queue_length())
                task = pop_from_queue(timeout=1)  # type: ignore[arg-type]
            except Exception as exc:  # noqa: BLE001
                logger.error("Redis pop error: %s", exc)
                task = None

            if task is None:
                await asyncio.sleep(POLL_INTERVAL)
                break

            try:
                await _process_task(page, task)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unhandled error while processing task %s: %s", task, exc)

            await asyncio.sleep(random.randint(1,3))  # light throttle to avoid hammering

    except asyncio.CancelledError:  # graceful shutdown by external signal
        logger.warning("Cancellation requested – shutting down.")
    finally:
        # ensure file + browser closed
        if _ndjson_file is not None:
            _ndjson_file.close()
            logger.info("NDJSON file closed.")
        await asyncio.gather(page.close(), browser.close())
        await playwright.stop()
        logger.info("Playwright stopped – bye.")


# ---------------------------------------------------------------------------
# CLI entry‑point
# ---------------------------------------------------------------------------

def main() -> None:  # pragma: no cover
    try:
        asyncio.run(_event_loop())
    except KeyboardInterrupt:
        logger.warning("Interrupted by user – exiting.")


if __name__ == "__main__":
    main()
