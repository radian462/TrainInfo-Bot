# test_database.py
from unittest.mock import patch

from Modules.traininfo.database import (TrainStatus, get_previous_status,
                                        set_latest_status)


@patch("Modules.traininfo.database.r")
def test_save_and_load(mock_redis):
    data = [TrainStatus(train="山手線", status="平常運転", detail="On time")]
    storage = {}

    mock_redis.set.side_effect = lambda k, v: storage.setdefault(k, v)
    mock_redis.get.side_effect = lambda k: storage.get(k)

    set_latest_status("KANTO", data)
    result = get_previous_status("KANTO")

    assert result == tuple(data)
