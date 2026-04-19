from traininfo.normalizer import status_normalizer


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


def test_nhk_code():
    assert status_normalizer(NHK_code="00") == "🚋平常運転"
    assert status_normalizer(NHK_code="06") == "🚋平常運転"
    assert status_normalizer(NHK_code="01") == "🛑運転見合わせ"
    assert status_normalizer(NHK_code="02") == "🚋運転再開"
    assert status_normalizer(NHK_code="03") == "🕒ダイヤ乱れ"
    assert status_normalizer(NHK_code="04") == "🗒️運転計画"
    assert status_normalizer(NHK_code="07") == "⚠️その他"
    assert status_normalizer(NHK_code="08") == "⚠️その他"


def test_nhk_unknown_code_falls_back_to_other():
    assert status_normalizer(NHK_code="99") == "⚠️その他"


def test_no_args_returns_other():
    assert status_normalizer() == "⚠️その他"


def test_none_status_returns_other():
    assert status_normalizer(None) == "⚠️その他"


def test_nhk_code_takes_priority_over_status():
    # NHK_code="00" は平常運転。status は無視されるべき
    assert status_normalizer(status="運転見合わせ", NHK_code="00") == "🚋平常運転"
