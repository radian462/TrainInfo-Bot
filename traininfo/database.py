import json
import os
from dataclasses import asdict

from dotenv import load_dotenv
from redis import Redis

from utils.make_logger import make_logger

from .request import TrainStatus

load_dotenv()
logger = make_logger("database")

r: Redis | None = None
upstash_host = os.getenv("UPSTASH_HOST")
upstash_port = os.getenv("UPSTASH_PORT")
upstash_pass = os.getenv("UPSTASH_PASS")

if upstash_host and upstash_port and upstash_pass:
    r = Redis(
        host=upstash_host,
        port=int(upstash_port),
        password=upstash_pass,
        ssl=True,
        decode_responses=True,
    )

if r is None:
    logger.warning("Redis client is not initialized.")


def set_latest_status(region_db: str, data: list[TrainStatus]) -> None:
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
