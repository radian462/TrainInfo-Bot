from enums import AuthType, Region, Service


def test_region_kanto_properties():
    # KANTO 地域の label と id が正しいこと
    assert Region.KANTO.label == "kanto"
    assert Region.KANTO.id == 4


def test_region_kansai_properties():
    # KANSAI 地域の label と id が正しいこと
    assert Region.KANSAI.label == "kansai"
    assert Region.KANSAI.id == 6


def test_service_bluesky_label():
    # Bluesky サービスの label が "Bluesky" であること
    assert Service.BLUESKY.label == "Bluesky"


def test_service_misskeyio_label():
    # MisskeyIO サービスの label が "MisskeyIO" であること
    assert Service.MISSKEYIO.label == "MisskeyIO"


def test_auth_type_username_password():
    # USERNAME_PASSWORD 認証タイプの value が "username_password" であること
    assert AuthType.USERNAME_PASSWORD.value == "username_password"


def test_auth_type_token():
    # TOKEN 認証タイプの value が "token" であること
    assert AuthType.TOKEN.value == "token"
