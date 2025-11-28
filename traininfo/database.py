import json
import os
from dataclasses import asdict
from functools import lru_cache

from redis import Redis

from utils.make_logger import make_logger

from .trainstatus import TrainStatus

logger = make_logger(__name__)


def get_redis_client() -> Redis | None:
    @lru_cache(maxsize=1)
    def _create_client() -> Redis | None:
        REDIS_HOST = os.getenv("UPSTASH_HOST")
        REDIS_PORT = os.getenv("UPSTASH_PORT")
        REDIS_PASS = os.getenv("UPSTASH_PASS")

        if not REDIS_HOST or not REDIS_PORT or not REDIS_PASS:
            return None

        return Redis(
            host=REDIS_HOST,
            port=int(REDIS_PORT),
            password=REDIS_PASS,
            ssl=True,
            decode_responses=True,
        )

    r = _create_client()
    if r is None:
        _create_client.cache_clear()
    return r


def set_latest_status(region_db: str, data: list[TrainStatus]) -> None:
    r = get_redis_client()
    if r is None:
        logger.warning("Redis client is not available. Skipping set operation.")
        return

    try:
        set_data = [asdict(s) for s in data]
        r.set(region_db, json.dumps(set_data))
        logger.info(f"Saved {len(data)} train status records to Redis ({region_db})")
    except Exception:
        logger.error("An error occurred while sending data to Redis", exc_info=True)


def get_previous_status(region_db: str) -> tuple[TrainStatus, ...]:
    r = get_redis_client()
    if r is None:
        logger.warning("Redis client is not available. Returning empty tuple.")
        return tuple()

    try:
        data = r.get(region_db)  # type: ignore[misc]
        if data is None:
            return tuple()

        loaded_data = json.loads(data)  # type: ignore[arg-type]
        return tuple(TrainStatus(**d) for d in loaded_data)
    except Exception:
        logger.error("An error occurred while fetching data from Redis", exc_info=True)
        return tuple()
