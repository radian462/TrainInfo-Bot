from unittest.mock import Mock, patch

import pytest

from Modules.traininfo.request import (TrainStatus, request_from_NHK,
                                       request_from_yahoo)


@pytest.fixture
def sample_nhk_response():
    return {
        "channel": {
            "item": [
                {
                    "trainLine": "山手線",
                    "status": "平常",
                    "textLong": "正常に運転しています",
                }
            ],
            "itemLong": [
                {"trainLine": "中央線", "status": "遅延", "textLong": "一部遅れあり"}
            ],
        }
    }


@pytest.fixture
def sample_yahoo_html():
    return """
    <html>
        <body>
            <script id="__NEXT_DATA__">
            {
                "props": {
                    "pageProps": {
                        "diainfoTrainFeatures": [
                            [
                                {
                                    "routeInfo": {
                                        "property": {
                                            "displayName": "山手線",
                                            "diainfo": [
                                                {
                                                    "status": "遅延",
                                                    "message": "大幅な遅れがあります。"
                                                }
                                            ]
                                        }
                                    }
                                }
                            ]
                        ]
                    }
                }
            }
            </script>
        </body>
    </html>
    """


@patch("Modules.traininfo.request.requests.get")
def test_request_from_NHK(mock_get, sample_nhk_response):
    mock_response = Mock()
    mock_response.json.return_value = sample_nhk_response
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = request_from_NHK(1)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], TrainStatus)
    assert result[0].train == "山手線"


@patch("Modules.traininfo.request.session.get")
def test_request_from_yahoo(mock_get, sample_yahoo_html):
    mock_response = Mock()
    mock_response.content = sample_yahoo_html.encode("utf-8")
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = request_from_yahoo(1)
    assert isinstance(result, tuple)
    assert len(result) == 1
    assert result[0].train == "山手線"
    assert result[0].status == "遅延"


@patch("Modules.traininfo.request.session.get")
def test_request_from_yahoo_no_next_data(mock_get):
    mock_response = Mock()
    mock_response.content = "<html><body>No script tag</body></html>".encode("utf-8")
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = request_from_yahoo(1)
    assert result is None
