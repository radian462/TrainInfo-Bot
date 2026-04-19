from enums import AuthType, Region, Service


def test_region_kanto_properties():
    assert Region.KANTO.label == "kanto"
    assert Region.KANTO.id == 4


def test_region_kansai_properties():
    assert Region.KANSAI.label == "kansai"
    assert Region.KANSAI.id == 6


def test_service_bluesky_label():
    assert Service.BLUESKY.label == "Bluesky"


def test_service_misskeyio_label():
    assert Service.MISSKEYIO.label == "MisskeyIO"


def test_auth_type_username_password():
    assert AuthType.USERNAME_PASSWORD.value == "username_password"


def test_auth_type_token():
    assert AuthType.TOKEN.value == "token"
