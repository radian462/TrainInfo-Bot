from unittest.mock import MagicMock, patch

from enums import Region
from traininfo.request import TrainInfoClient
from traininfo.sources.baseclient import TrainInfoResponse
from traininfo.trainstatus import TrainStatus

_DUMMY_STATUS = (TrainStatus(train="山手線", status="🚋平常運転", detail=""),)


def test_request_returns_success():
    # NHK クライアントが成功した場合、その結果が返ること
    with patch("traininfo.request.NHKClient") as MockNHK:
        mock_nhk = MagicMock()
        MockNHK.return_value = mock_nhk
        mock_nhk.request.return_value = TrainInfoResponse(
            is_success=True, data=_DUMMY_STATUS
        )

        client = TrainInfoClient(region=Region.KANTO, yahoo_app_id=None)
        result = client.request()

        assert result.is_success is True
        assert result.data == _DUMMY_STATUS


def test_request_returns_failure_when_all_clients_fail():
    # 全クライアントが失敗した場合、エラーメッセージが返ること
    with patch("traininfo.request.NHKClient") as MockNHK:
        mock_nhk = MagicMock()
        MockNHK.return_value = mock_nhk
        mock_nhk.request.return_value = TrainInfoResponse(
            is_success=False, data=None, error="fetch error"
        )

        client = TrainInfoClient(region=Region.KANTO, yahoo_app_id=None)
        result = client.request()

        assert result.is_success is False
        assert result.error == "All sources failed to retrieve data."


def test_yahoo_has_higher_priority_than_nhk():
    # yahoo_app_id が指定された場合、Yahoo が NHK より先に試みられること
    with (
        patch("traininfo.request.NHKClient") as MockNHK,
        patch("traininfo.request.YahooClient") as MockYahoo,
    ):
        mock_nhk = MagicMock()
        mock_yahoo = MagicMock()
        MockNHK.return_value = mock_nhk
        MockYahoo.return_value = mock_yahoo

        mock_yahoo.request.return_value = TrainInfoResponse(
            is_success=True, data=_DUMMY_STATUS
        )

        client = TrainInfoClient(region=Region.KANTO, yahoo_app_id="test_id")
        result = client.request()

        mock_yahoo.request.assert_called_once()
        mock_nhk.request.assert_not_called()
        assert result.is_success is True


def test_falls_back_to_nhk_when_yahoo_fails():
    # Yahoo が失敗した場合、NHK にフォールバックして結果が返ること
    with (
        patch("traininfo.request.NHKClient") as MockNHK,
        patch("traininfo.request.YahooClient") as MockYahoo,
    ):
        mock_nhk = MagicMock()
        mock_yahoo = MagicMock()
        MockNHK.return_value = mock_nhk
        MockYahoo.return_value = mock_yahoo

        mock_yahoo.request.return_value = TrainInfoResponse(
            is_success=False, data=None, error="yahoo error"
        )
        mock_nhk.request.return_value = TrainInfoResponse(
            is_success=True, data=_DUMMY_STATUS
        )

        client = TrainInfoClient(region=Region.KANTO, yahoo_app_id="test_id")
        result = client.request()

        mock_yahoo.request.assert_called_once()
        mock_nhk.request.assert_called_once()
        assert result.is_success is True
        assert result.data == _DUMMY_STATUS


def test_yahoo_not_registered_without_app_id():
    # yahoo_app_id が None の場合、Yahoo クライアントが登録されないこと
    with (
        patch("traininfo.request.NHKClient") as MockNHK,
        patch("traininfo.request.YahooClient") as MockYahoo,
    ):
        MockNHK.return_value = MagicMock()
        MockNHK.return_value.request.return_value = TrainInfoResponse(
            is_success=True, data=_DUMMY_STATUS
        )

        client = TrainInfoClient(region=Region.KANTO, yahoo_app_id=None)

        MockYahoo.assert_not_called()
        assert len(client.clients) == 1
