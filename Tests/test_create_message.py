import pytest
from types import SimpleNamespace

TrainStatus = SimpleNamespace

from Modules.traininfo.message import create_message 


def test_incident_to_another():
    previous = (
        TrainStatus(train="山手線", status="🚋平常運転", detail="問題なし"),
    )
    latest = (
        TrainStatus(train="山手線", status="🚋遅延", detail="5分程度の遅れ"),
    )

    result = create_message(latest, previous)
    assert result is not None
    assert result[0] == "山手線 : 🚋平常運転➡️🚋遅延\n5分程度の遅れ"

def test_new_incident():
    previous = (
        TrainStatus(train="山手線", status="🚋平常運転", detail="問題なし"),
    )
    latest = (
        TrainStatus(train="山手線", status="🚋平常運転", detail="問題なし"),
        TrainStatus(train="中央線", status="🚋遅延", detail="線路内立ち入り"),
    )

    result = create_message(latest, previous)
    assert result is not None
    assert result == ["中央線 : 🚋平常運転➡️🚋遅延\n線路内立ち入り"]

def test_resolved_incident():
    previous = (
        TrainStatus(train="山手線", status="🚋遅延", detail="5分程度の遅れ"),
    )
    latest = (
        TrainStatus(train="山手線", status="🚋平常運転", detail="問題なし"),
    )

    result = create_message(latest, previous)
    assert result is not None
    assert result[0] == "山手線 : 🚋遅延➡️🚋平常運転\n問題なし"

def test_unchanged_incident():
    previous = (
        TrainStatus(train="山手線", status="🚋遅延", detail="5分程度の遅れ"),
    )
    latest = (
        TrainStatus(train="中央線", status="🚋遅延", detail="線路内立ち入り"),
        TrainStatus(train="山手線", status="🚋遅延", detail="5分程度の遅れ"),
    )

    result = create_message(latest, previous)
    assert result is not None
    assert result[0] == "中央線 : 🚋平常運転➡️🚋遅延\n線路内立ち入り\n\n山手線 : 🚋遅延\n5分程度の遅れ"

