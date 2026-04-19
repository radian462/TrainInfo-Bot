from datetime import datetime, timedelta, timezone

from clients.bluesky import BlueskyClient


def _make_client() -> BlueskyClient:
    return BlueskyClient()


def test_parse_uri_valid():
    client = _make_client()
    uri = "at://did:plc:abc123/app.bsky.feed.post/rkey123"
    result = client._parse_uri(uri)
    assert result["repo"] == "did:plc:abc123"
    assert result["collection"] == "app.bsky.feed.post"
    assert result["rkey"] == "rkey123"


def test_parse_uri_too_short_returns_empty():
    client = _make_client()
    result = client._parse_uri("invalid")
    assert result == {}


def test_parse_uri_empty_string_returns_empty():
    client = _make_client()
    result = client._parse_uri("")
    assert result == {}


def test_should_refresh_when_no_last_refresh():
    client = _make_client()
    assert client.last_refresh is None
    assert client._should_refresh() is True


def test_should_refresh_false_when_recently_refreshed():
    client = _make_client()
    client.last_refresh = datetime.now(timezone.utc)
    assert client._should_refresh() is False


def test_should_refresh_true_when_expired():
    client = _make_client()
    client.last_refresh = datetime.now(timezone.utc) - timedelta(
        seconds=client.refresh_interval + 1
    )
    assert client._should_refresh() is True


def test_login_missing_identifier():
    client = _make_client()
    result = client.login(None, "password")
    assert result is False


def test_login_missing_password():
    client = _make_client()
    result = client.login("user@example.com", None)
    assert result is False


def test_login_missing_both_credentials():
    client = _make_client()
    result = client.login(None, None)
    assert result is False


def test_post_without_login_returns_failure():
    client = _make_client()
    result = client.post("Hello")
    assert result.success is False
    assert result.error == "Not logged in"
