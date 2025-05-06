"""redis_queue.py
--------------------------------------------------------------------
Thin, functional wrapper around Redis for a single list‑based task queue.
Includes structured logging, connection‑pooling and robust error trapping.
--------------------------------------------------------------------
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import redis
from redis.exceptions import RedisError

# ---------------------------------------------------------------------------
# Configuration via environment variables (all optional)
# ---------------------------------------------------------------------------
REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
QUEUE_NAME: str = os.getenv("REDIS_QUEUE_NAME", "crawl_links")
POP_TIMEOUT: int = int(os.getenv("REDIS_QUEUE_POP_TIMEOUT", "0"))  # seconds (0 = non‑blocking)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("redis_queue")
if not logger.handlers:  # honour root config if present
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")

# ---------------------------------------------------------------------------
# Redis connection (singleton via connection‑pool for thread‑safety)
# ---------------------------------------------------------------------------
_pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,
    max_connections=10,
)
_redis: redis.Redis = redis.Redis(connection_pool=_pool)


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _json_dumps(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError) as exc:  # pragma: no cover
        logger.error("JSON serialisation failed: %s", exc)
        raise


def _json_loads(s: str) -> Dict[str, Any] | None:
    try:
        return json.loads(s)
    except json.JSONDecodeError as exc:  # pragma: no cover
        logger.warning("Skipping invalid JSON: %s", exc)
        return None

# ---------------------------------------------------------------------------
# Public queue API
# ---------------------------------------------------------------------------

def add_to_queue(link: str, row_type: str) -> None:
    """Enqueue a crawl task.

    Parameters
    ----------
    link
        Full URL to crawl.
    row_type
        Tag to describe the link (e.g. ``"new"`` or ``"modified"``).
    """
    payload = _json_dumps({"url": link, "row_type": row_type})
    try:
        _redis.rpush(QUEUE_NAME, payload)
        logger.debug("Pushed %s (%s) – length=%d", link, row_type, _redis.llen(QUEUE_NAME))
    except RedisError as exc:
        logger.error("Redis push failed: %s", exc)
        raise


def pop_from_queue(block: bool = False, timeout: int | None = None) -> Dict[str, Any] | None:
    """Pop a task from the queue.

    Parameters
    ----------
    block
        Use BLPOP (blocking) instead of LPOP.
    timeout
        Seconds to wait when *block* is True (None = forever). Ignored otherwise.
    """
    try:
        data: str | None
        if block:
            timeout = POP_TIMEOUT if timeout is None else timeout
            pair = _redis.blpop(QUEUE_NAME, timeout=timeout)
            data = pair[1] if pair else None
        else:
            data = _redis.lpop(QUEUE_NAME)

        return _json_loads(data) if data else None
    except RedisError as exc:
        logger.error("Redis pop failed: %s", exc)
        return None


def queue_length() -> int:
    """Return queue length (‑1 if unreachable)."""
    try:
        return _redis.llen(QUEUE_NAME)
    except RedisError as exc:
        logger.error("Redis length failed: %s", exc)
        return -1


def clear_queue() -> None:
    """Delete the whole queue (dangerous!)."""
    try:
        _redis.delete(QUEUE_NAME)
        logger.info("Queue '%s' cleared", QUEUE_NAME)
    except RedisError as exc:
        logger.error("Redis delete failed: %s", exc)


def peek_queue(n: int = 5) -> List[Dict[str, Any]]:
    """Return the first *n* items without removing them."""
    try:
        items = _redis.lrange(QUEUE_NAME, 0, n - 1)
        return [d for s in items if (d := _json_loads(s))]
    except RedisError as exc:
        logger.error("Redis LRANGE failed: %s", exc)
        return []
