import json
import os
from dataclasses import asdict

from redis import Redis

from ..make_logger import make_logger
from .request import TrainStatus

r: Redis | None = None
if os.getenv("UPSTASH_PORT"):
    r = Redis(
        host=os.getenv("UPSTASH_HOST"),
        port=int(os.getenv("UPSTASH_PORT")),
        password=os.getenv("UPSTASH_PASS"),
        ssl=True,
        decode_responses=True,
    )


logger = make_logger("database")


def set_latest_status(region_db: str, data: list[TrainStatus]) -> None:
    try:
        set_data = [asdict(s) for s in data]
        r.set(region_db, json.dumps(set_data))
        logger.info(f"Saved {len(data)} train status records to Redis ({region_db})")
    except Exception:
        logger.error("An error occurred while sending data to Redis", exc_info=True)


def get_previous_status(region_db: str) -> tuple[TrainStatus, ...]:
    try:
        data = r.get(region_db)
        if data:
            loaded_data = json.loads(data)
            return tuple(TrainStatus(**d) for d in loaded_data)
        else:
            return None
    except Exception:
        logger.error("An error occurred while fetching data from Redis", exc_info=True)
        return tuple()
