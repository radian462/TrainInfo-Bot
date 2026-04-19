from json import JSONDecodeError
from unittest.mock import MagicMock, patch

import requests

from enums import Region
from traininfo.sources.baseclient import BaseTrainInfoClient
from traininfo.trainstatus import TrainStatus


class _ConcreteClient(BaseTrainInfoClient):
    """Concrete implementation of BaseTrainInfoClient for testing."""

    def __init__(self, session, region, fetch_side_effect=None, fetch_return=None):
        super().__init__(session=session, region=region, retry_sleep=0, retry_times=3)
        self._fetch_side_effect = fetch_side_effect
        self._fetch_return = fetch_return
        self.fetch_call_count = 0

    def _fetch(self):
        self.fetch_call_count += 1
        if self._fetch_side_effect is not None:
            raise self._fetch_side_effect
        return self._fetch_return

    def _parse(self, raw):
        return (TrainStatus(train="山手線", status="🚋平常運転", detail=""),)


def _make_client(fetch_side_effect=None, fetch_return=None) -> _ConcreteClient:
    session = MagicMock()
    return _ConcreteClient(
        session=session,
        region=Region.KANTO,
        fetch_side_effect=fetch_side_effect,
        fetch_return=fetch_return,
    )


def test_request_success():
    client = _make_client(fetch_return={"ok": True})
    result = client.request()
    assert result.is_success is True
    assert result.data == (TrainStatus(train="山手線", status="🚋平常運転", detail=""),)
    assert result.error is None
    assert client.fetch_call_count == 1


def test_request_json_decode_error_no_retry():
    client = _make_client(fetch_side_effect=JSONDecodeError("err", "doc", 0))
    result = client.request()
    assert result.is_success is False
    assert client.fetch_call_count == 1


def test_request_value_error_no_retry():
    client = _make_client(fetch_side_effect=ValueError("invalid value"))
    result = client.request()
    assert result.is_success is False
    assert client.fetch_call_count == 1


@patch("time.sleep")
def test_request_timeout_retries(mock_sleep):
    client = _make_client(fetch_side_effect=requests.Timeout())
    result = client.request()
    assert result.is_success is False
    assert client.fetch_call_count == 3


@patch("time.sleep")
def test_request_500_retries(mock_sleep):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.headers = {}
    err = requests.HTTPError(response=mock_response)
    client = _make_client(fetch_side_effect=err)
    result = client.request()
    assert result.is_success is False
    assert client.fetch_call_count == 3


@patch("time.sleep")
def test_request_404_no_retry(mock_sleep):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.headers = {}
    err = requests.HTTPError(response=mock_response)
    client = _make_client(fetch_side_effect=err)
    result = client.request()
    assert result.is_success is False
    assert client.fetch_call_count == 1


@patch("time.sleep")
def test_request_429_retries_with_retry_after(mock_sleep):
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "5"}
    err = requests.HTTPError(response=mock_response)
    client = _make_client(fetch_side_effect=err)
    result = client.request()
    assert result.is_success is False
    assert client.fetch_call_count == 3
    mock_sleep.assert_called()


@patch("time.sleep")
def test_request_429_retries_without_retry_after(mock_sleep):
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {}
    err = requests.HTTPError(response=mock_response)
    client = _make_client(fetch_side_effect=err)
    result = client.request()
    assert result.is_success is False
    assert client.fetch_call_count == 3


def test_status_exception_handler_429_with_retry_after():
    client = _make_client()
    mock_response = MagicMock()
    mock_response.headers = {"Retry-After": "30"}
    err = requests.HTTPError(response=mock_response)
    is_retry, delay = client._status_exception_handler(429, err, 0)
    assert is_retry is True
    assert delay == 30.0


def test_status_exception_handler_429_exponential_backoff():
    client = _make_client()
    mock_response = MagicMock()
    mock_response.headers = {}
    err = requests.HTTPError(response=mock_response)
    is_retry, delay = client._status_exception_handler(429, err, 2)
    assert is_retry is True
    assert delay == 4.0  # 2**2


def test_status_exception_handler_500():
    client = _make_client()
    mock_response = MagicMock()
    err = requests.HTTPError(response=mock_response)
    is_retry, delay = client._status_exception_handler(500, err, 0)
    assert is_retry is True
    assert delay is None


def test_status_exception_handler_404():
    client = _make_client()
    mock_response = MagicMock()
    err = requests.HTTPError(response=mock_response)
    is_retry, delay = client._status_exception_handler(404, err, 0)
    assert is_retry is False
    assert delay is None
