from datetime import datetime, timedelta, timezone

from clients.bluesky import BlueskyClient


def _make_client() -> BlueskyClient:
    return BlueskyClient()


def test_parse_uri_valid():
    # 正常な AT URI が repo / collection / rkey に正しく分解されること
    client = _make_client()
    uri = "at://did:plc:abc123/app.bsky.feed.post/rkey123"
    result = client._parse_uri(uri)
    assert result["repo"] == "did:plc:abc123"
    assert result["collection"] == "app.bsky.feed.post"
    assert result["rkey"] == "rkey123"


def test_parse_uri_too_short_returns_empty():
    # セグメント数が不足する不正な URI の場合、空辞書が返ること
    client = _make_client()
    result = client._parse_uri("invalid")
    assert result == {}


def test_parse_uri_empty_string_returns_empty():
    # 空文字列を渡した場合、空辞書が返ること
    client = _make_client()
    result = client._parse_uri("")
    assert result == {}


def test_should_refresh_when_no_last_refresh():
    # 最終リフレッシュ時刻が未設定の場合、リフレッシュが必要と判定されること
    client = _make_client()
    assert client.last_refresh is None
    assert client._should_refresh() is True


def test_should_refresh_false_when_recently_refreshed():
    # 直近にリフレッシュ済みの場合、リフレッシュ不要と判定されること
    client = _make_client()
    client.last_refresh = datetime.now(timezone.utc)
    assert client._should_refresh() is False


def test_should_refresh_true_when_expired():
    # リフレッシュ期限が切れている場合、リフレッシュが必要と判定されること
    client = _make_client()
    client.last_refresh = datetime.now(timezone.utc) - timedelta(
        seconds=client.refresh_interval + 1
    )
    assert client._should_refresh() is True


def test_login_missing_identifier():
    # identifier が None の場合、ログインが失敗すること
    client = _make_client()
    result = client.login(None, "password")
    assert result is False


def test_login_missing_password():
    # password が None の場合、ログインが失敗すること
    client = _make_client()
    result = client.login("user@example.com", None)
    assert result is False


def test_login_missing_both_credentials():
    # identifier と password の両方が None の場合、ログインが失敗すること
    client = _make_client()
    result = client.login(None, None)
    assert result is False


def test_post_without_login_returns_failure():
    # ログインせずに投稿しようとした場合、失敗が返ること
    client = _make_client()
    result = client.post("Hello")
    assert result.success is False
    assert result.error == "Not logged in"
