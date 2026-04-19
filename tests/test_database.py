# test_database.py
from unittest.mock import MagicMock, patch

from traininfo.database import (
    TrainStatus,
    get_previous_status,
    set_latest_status,
)


@patch("traininfo.database.get_redis_client")
def test_save_and_load(mock_get_redis_client):
    # 状態を保存し、その後読み込むと同じデータが返ること
    mock_redis = MagicMock()
    mock_get_redis_client.return_value = mock_redis

    data = [TrainStatus(train="山手線", status="平常運転", detail="On time")]
    storage = {}

    mock_redis.set.side_effect = lambda k, v: storage.setdefault(k, v)
    mock_redis.get.side_effect = lambda k: storage.get(k)

    set_latest_status("KANTO", data)
    result = get_previous_status("KANTO")

    assert result == tuple(data)


@patch("traininfo.database.get_redis_client")
def test_get_previous_status_redis_unavailable(mock_get_redis_client):
    # Redis クライアントが利用不可の場合、空のタプルが返ること
    mock_get_redis_client.return_value = None
    result = get_previous_status("KANTO")
    assert result == tuple()


@patch("traininfo.database.get_redis_client")
def test_get_previous_status_key_not_found(mock_get_redis_client):
    # Redis にキーが存在しない場合、空のタプルが返ること
    mock_redis = MagicMock()
    mock_get_redis_client.return_value = mock_redis
    mock_redis.get.return_value = None
    result = get_previous_status("KANTO")
    assert result == tuple()


@patch("traininfo.database.get_redis_client")
def test_get_previous_status_exception_returns_empty(mock_get_redis_client):
    # Redis の get で例外が発生した場合、空のタプルが返ること
    mock_redis = MagicMock()
    mock_get_redis_client.return_value = mock_redis
    mock_redis.get.side_effect = Exception("connection error")
    result = get_previous_status("KANTO")
    assert result == tuple()


@patch("traininfo.database.get_redis_client")
def test_set_latest_status_redis_unavailable(mock_get_redis_client):
    # Redis クライアントが利用不可の場合、例外を出さず正常終了すること
    mock_get_redis_client.return_value = None
    # Should not raise even when Redis is unavailable
    set_latest_status("KANTO", [TrainStatus(train="山手線", status="平常運転", detail="")])


@patch("traininfo.database.get_redis_client")
def test_set_latest_status_exception_is_handled(mock_get_redis_client):
    # Redis の set で例外が発生した場合、例外を出さず正常終了すること
    mock_redis = MagicMock()
    mock_get_redis_client.return_value = mock_redis
    mock_redis.set.side_effect = Exception("write error")
    # Should not raise
    set_latest_status("KANTO", [TrainStatus(train="山手線", status="平常運転", detail="")])
