import json
import os
from dataclasses import asdict
from functools import lru_cache

from redis import Redis

from utils.make_logger import make_logger

from .trainstatus import TrainStatus

logger = make_logger(__name__)


def get_redis_client() -> Redis | None:
    """
    Redisクライアントを作成。一度作成したらキャッシュする。
    Noneの場合はキャッシュクリア。

    Returns
    -------
    Redis | None
        Redisクライアントのインスタンス。作成に失敗した場合はNone。
    """

    @lru_cache(maxsize=1)
    def _create_client() -> Redis | None:
        REDIS_HOST = os.getenv("UPSTASH_HOST")
        REDIS_PORT = os.getenv("UPSTASH_PORT")
        REDIS_PASS = os.getenv("UPSTASH_PASS")
        return Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASS,
            ssl=True,
            decode_responses=True,
        )

    r = _create_client()
    if r is None:
        _create_client.cache_clear()
    return r


def set_latest_status(region_db: str, data: list[TrainStatus]) -> None:
    """
    最新の運行情報をRedisに保存する。

    Parameters
    ----------
    region_db : str
        データベース名。
    data : list[TrainStatus]
        保存する運行情報のリスト。
    """
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
    """
    Redisから運行情報のキャッシュを取得する。

    Parameters
    ----------
    region_db : str
        データベース名。

    Returns
    -------
    tuple[TrainStatus, ...]
        取得した運行情報のタプル。データが存在しない場合は空のタプルを返す。
    """
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
