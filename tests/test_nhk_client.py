from unittest.mock import MagicMock

from enums import Region
from traininfo.sources.nhk import NHKClient


def _make_nhk_client() -> NHKClient:
    session = MagicMock()
    return NHKClient(session=session, region=Region.KANTO)


def test_parse_normal_status():
    client = _make_nhk_client()
    raw = {
        "channel": {
            "item": [
                {
                    "trainLine": "山手線",
                    "detailStatusCode": "00",
                    "detailStatusName": "平常運転",
                    "textLong": "",
                }
            ],
            "itemLong": [],
        }
    }
    result = client._parse(raw)
    assert len(result) == 1
    assert result[0].train == "山手線"
    assert result[0].status == "🚋平常運転"
    assert result[0].detail == ""


def test_parse_delay_status():
    client = _make_nhk_client()
    raw = {
        "channel": {
            "item": [
                {
                    "trainLine": "中央線",
                    "detailStatusCode": "03",
                    "detailStatusName": "ダイヤ乱れ",
                    "textLong": "遅れが発生しています",
                }
            ],
            "itemLong": [],
        }
    }
    result = client._parse(raw)
    assert len(result) == 1
    assert result[0].train == "中央線"
    assert result[0].status == "🕒ダイヤ乱れ"
    assert result[0].detail == "遅れが発生しています"


def test_parse_suspended_status():
    client = _make_nhk_client()
    raw = {
        "channel": {
            "item": [
                {
                    "trainLine": "東海道線",
                    "detailStatusCode": "01",
                    "detailStatusName": "運転見合わせ",
                    "textLong": "運転を見合わせています",
                }
            ],
            "itemLong": [],
        }
    }
    result = client._parse(raw)
    assert result[0].status == "🛑運転見合わせ"


def test_parse_item_long():
    client = _make_nhk_client()
    raw = {
        "channel": {
            "item": [],
            "itemLong": [
                {
                    "trainLine": "横浜線",
                    "detailStatusCode": "02",
                    "detailStatusName": "運転再開",
                    "textLong": "運転を再開しました",
                }
            ],
        }
    }
    result = client._parse(raw)
    assert len(result) == 1
    assert result[0].train == "横浜線"
    assert result[0].status == "🚋運転再開"


def test_parse_merges_item_and_item_long():
    client = _make_nhk_client()
    raw = {
        "channel": {
            "item": [
                {
                    "trainLine": "山手線",
                    "detailStatusCode": "00",
                    "detailStatusName": "平常運転",
                    "textLong": "",
                }
            ],
            "itemLong": [
                {
                    "trainLine": "中央線",
                    "detailStatusCode": "01",
                    "detailStatusName": "運転見合わせ",
                    "textLong": "詳細",
                }
            ],
        }
    }
    result = client._parse(raw)
    assert len(result) == 2


def test_parse_empty_channel():
    client = _make_nhk_client()
    raw = {"channel": {"item": [], "itemLong": []}}
    result = client._parse(raw)
    assert result == tuple()


def test_parse_missing_channel():
    client = _make_nhk_client()
    raw = {}
    result = client._parse(raw)
    assert result == tuple()


def test_parse_filters_non_dict_items():
    client = _make_nhk_client()
    raw = {
        "channel": {
            "item": [
                "invalid_string",
                None,
                {
                    "trainLine": "山手線",
                    "detailStatusCode": "00",
                    "detailStatusName": "平常運転",
                    "textLong": "",
                },
            ],
            "itemLong": [],
        }
    }
    result = client._parse(raw)
    assert len(result) == 1
    assert result[0].train == "山手線"


def test_parse_uses_status_name_when_no_nhk_code_match():
    client = _make_nhk_client()
    raw = {
        "channel": {
            "item": [
                {
                    "trainLine": "京浜東北線",
                    "detailStatusCode": "",
                    "detailStatusName": "交通障害情報",
                    "textLong": "周辺で交通障害が発生",
                }
            ],
            "itemLong": [],
        }
    }
    result = client._parse(raw)
    assert result[0].status == "🚧交通障害情報"
