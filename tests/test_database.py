# test_database.py
from unittest.mock import MagicMock, patch

from traininfo.database import (
    TrainStatus,
    get_previous_status,
    set_latest_status,
)


@patch("traininfo.database.get_redis_client")
def test_save_and_load(mock_get_redis_client):
    mock_redis = MagicMock()
    mock_get_redis_client.return_value = mock_redis

    data = [TrainStatus(train="山手線", status="平常運転", detail="On time")]
    storage = {}

    mock_redis.set.side_effect = lambda k, v: storage.setdefault(k, v)
    mock_redis.get.side_effect = lambda k: storage.get(k)

    set_latest_status("KANTO", data)
    result = get_previous_status("KANTO")

    assert result == tuple(data)
