from unittest.mock import MagicMock

import requests

from enums import Region
from traininfo.sources.yahoo import YahooClient


def _make_yahoo_client() -> YahooClient:
    session = MagicMock()
    return YahooClient(session=session, region=Region.KANTO, yahoo_app_id="test_app_id")


def test_parse_normal_status():
    # 平常運転の feature が正しくパースされること
    client = _make_yahoo_client()
    raw = {
        "feature": [
            {
                "routeInfo": {
                    "property": {
                        "displayName": "山手線",
                        "diainfo": [{"status": "平常運転", "message": ""}],
                    }
                }
            }
        ]
    }
    result = client._parse(raw)
    assert len(result) == 1
    assert result[0].train == "山手線"
    assert result[0].status == "🚋平常運転"
    assert result[0].detail == ""


def test_parse_delay_status():
    # 列車遅延の feature が正しくパースされること
    client = _make_yahoo_client()
    raw = {
        "feature": [
            {
                "routeInfo": {
                    "property": {
                        "displayName": "中央線",
                        "diainfo": [
                            {"status": "列車遅延", "message": "5分程度遅れています"}
                        ],
                    }
                }
            }
        ]
    }
    result = client._parse(raw)
    assert result[0].train == "中央線"
    assert result[0].status == "🕒列車遅延"
    assert result[0].detail == "5分程度遅れています"


def test_parse_suspended_status():
    # 運転見合わせの feature が正しくパースされること
    client = _make_yahoo_client()
    raw = {
        "feature": [
            {
                "routeInfo": {
                    "property": {
                        "displayName": "東海道線",
                        "diainfo": [
                            {"status": "運転見合わせ", "message": "運転見合わせ中"}
                        ],
                    }
                }
            }
        ]
    }
    result = client._parse(raw)
    assert result[0].status == "🛑運転見合わせ"


def test_parse_empty_features():
    # feature リストが空の場合、空のタプルが返ること
    client = _make_yahoo_client()
    raw = {"feature": []}
    result = client._parse(raw)
    assert result == tuple()


def test_parse_missing_feature_key():
    # feature キーが存在しない場合、空のタプルが返ること
    client = _make_yahoo_client()
    raw = {}
    result = client._parse(raw)
    assert result == tuple()


def test_parse_multiple_diainfo_entries():
    # 1 路線に複数の diainfo がある場合、件数分のステータスが返ること
    client = _make_yahoo_client()
    raw = {
        "feature": [
            {
                "routeInfo": {
                    "property": {
                        "displayName": "山手線",
                        "diainfo": [
                            {"status": "平常運転", "message": ""},
                            {"status": "列車遅延", "message": "遅延中"},
                        ],
                    }
                }
            }
        ]
    }
    result = client._parse(raw)
    assert len(result) == 2
    assert result[0].train == "山手線"
    assert result[1].train == "山手線"


def test_parse_multiple_features():
    # 複数の feature（路線）がある場合、全路線のステータスが返ること
    client = _make_yahoo_client()
    raw = {
        "feature": [
            {
                "routeInfo": {
                    "property": {
                        "displayName": "山手線",
                        "diainfo": [{"status": "平常運転", "message": ""}],
                    }
                }
            },
            {
                "routeInfo": {
                    "property": {
                        "displayName": "中央線",
                        "diainfo": [{"status": "列車遅延", "message": ""}],
                    }
                }
            },
        ]
    }
    result = client._parse(raw)
    assert len(result) == 2
    trains = {r.train for r in result}
    assert trains == {"山手線", "中央線"}


def test_status_exception_handler_403_no_retry():
    # 403 エラーの場合、リトライしないこと
    client = _make_yahoo_client()
    mock_response = MagicMock()
    err = requests.HTTPError(response=mock_response)
    is_retry, delay = client._status_exception_handler(403, err, 0)
    assert is_retry is False
    assert delay is None


def test_status_exception_handler_429_retries():
    # 429 エラーで Retry-After ヘッダがある場合、リトライして delay が返ること
    client = _make_yahoo_client()
    mock_response = MagicMock()
    mock_response.headers = {"Retry-After": "10"}
    err = requests.HTTPError(response=mock_response)
    is_retry, delay = client._status_exception_handler(429, err, 0)
    assert is_retry is True
    assert delay == 10.0


def test_status_exception_handler_500_retries():
    # 500 エラーの場合、リトライ対象で delay は None になること
    client = _make_yahoo_client()
    mock_response = MagicMock()
    err = requests.HTTPError(response=mock_response)
    is_retry, delay = client._status_exception_handler(500, err, 0)
    assert is_retry is True
    assert delay is None


def test_status_exception_handler_404_no_retry():
    # 404 エラーの場合、リトライしないこと
    client = _make_yahoo_client()
    mock_response = MagicMock()
    err = requests.HTTPError(response=mock_response)
    is_retry, delay = client._status_exception_handler(404, err, 0)
    assert is_retry is False
    assert delay is None
