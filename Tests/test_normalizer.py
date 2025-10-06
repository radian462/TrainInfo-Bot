import pytest

from Modules.traininfo.normalizer import status_normalizer


def test_known_status():
    assert status_normalizer("運転見合わせ") == "🛑運転見合わせ"
    assert status_normalizer("列車遅延") == "🕒列車遅延"
    assert status_normalizer("運転情報") == "ℹ️運転情報"
    assert status_normalizer("運転状況") == "ℹ️運転状況"
    assert status_normalizer("運転計画") == "🗒️運転計画"
    assert status_normalizer("交通障害情報") == "🚧交通障害情報"
    assert status_normalizer("運転再開") == "🚋運転再開"
    assert status_normalizer("平常運転") == "🚋平常運転"
    assert status_normalizer("その他") == "⚠️その他"


def test_unknown_status():
    assert status_normalizer("事故発生") == "⚠️その他"
    assert status_normalizer("点検中") == "⚠️その他"
    assert status_normalizer("") == "⚠️その他"


def test_partial_match():
    assert status_normalizer("事故による列車遅延") == "🕒列車遅延"
    assert status_normalizer("終日運転見合わせ") == "🛑運転見合わせ"
