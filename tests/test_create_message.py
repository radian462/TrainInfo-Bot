from types import SimpleNamespace

from traininfo.message import create_message

TrainStatus = SimpleNamespace


def test_incident_to_another():
    previous = (TrainStatus(train="山手線", status="🚋平常運転", detail="問題なし"),)
    latest = (TrainStatus(train="山手線", status="🚋遅延", detail="5分程度の遅れ"),)

    result = create_message(latest, previous)
    assert result is not None
    assert result[0] == "山手線 : 🚋平常運転➡️🚋遅延\n5分程度の遅れ"


def test_new_incident():
    previous = (TrainStatus(train="山手線", status="🚋平常運転", detail="問題なし"),)
    latest = (
        TrainStatus(train="山手線", status="🚋平常運転", detail="問題なし"),
        TrainStatus(train="中央線", status="🚋遅延", detail="線路内立ち入り"),
    )

    result = create_message(latest, previous)
    assert result is not None
    assert result == ["中央線 : 🚋平常運転➡️🚋遅延\n線路内立ち入り"]


def test_resolved_incident():
    previous = (TrainStatus(train="山手線", status="🚋遅延", detail="5分程度の遅れ"),)
    latest = (TrainStatus(train="山手線", status="🚋平常運転", detail="問題なし"),)

    result = create_message(latest, previous)
    assert result is not None
    assert result[0] == "山手線 : 🚋遅延➡️🚋平常運転\n問題なし"


def test_unchanged_incident():
    previous = (TrainStatus(train="山手線", status="🚋遅延", detail="5分程度の遅れ"),)
    latest = (
        TrainStatus(train="中央線", status="🚋遅延", detail="線路内立ち入り"),
        TrainStatus(train="山手線", status="🚋遅延", detail="5分程度の遅れ"),
    )

    result = create_message(latest, previous)
    assert result is not None
    assert (
        result[0]
        == "中央線 : 🚋平常運転➡️🚋遅延\n線路内立ち入り\n\n山手線 : 🚋遅延\n5分程度の遅れ"
    )


def test_normal_to_none():
    previous = (TrainStatus(train="山手線", status="🚋平常運転", detail="問題なし"),)
    latest = tuple()

    result = create_message(latest, previous)
    assert result is not None
    assert result[0] == "運行状況に変更はありません。"


def test_incident_to_none():
    previous = (TrainStatus(train="山手線", status="🚋遅延", detail="5分程度の遅れ"),)
    latest = tuple()

    result = create_message(latest, previous)
    assert result is not None
    assert result[0] == "山手線 : 🚋遅延➡️🚋平常運転\n現在、ほぼ平常通り運転しています。"


def test_none_to_incident():
    previous = tuple()
    latest = (TrainStatus(train="山手線", status="🚋遅延", detail="5分程度の遅れ"),)

    result = create_message(latest, previous)
    assert result is not None
    assert result[0] == "山手線 : 🚋平常運転➡️🚋遅延\n5分程度の遅れ"


def test_message_splitting_by_width():
    long_detail = "x" * 200
    latest = (
        TrainStatus(train="路線A", status="🕒列車遅延", detail=long_detail),
        TrainStatus(train="路線B", status="🕒列車遅延", detail=long_detail),
    )
    previous = tuple()

    result = create_message(latest, previous, width=300)

    # Each message is ~219 chars; two together exceed 300, so they must split
    assert len(result) == 2
    for msg in result:
        assert len(msg) <= 300


def test_many_incidents_split_into_multiple_messages():
    latest = tuple(
        TrainStatus(train=f"路線{i:02d}", status="🕒列車遅延", detail="遅延が発生しています")
        for i in range(10)
    )
    previous = tuple()

    result = create_message(latest, previous, width=100)

    assert len(result) > 1
    for msg in result:
        assert len(msg) <= 100
