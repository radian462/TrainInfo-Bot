from types import SimpleNamespace

from traininfo.message import sort_status

TrainStatus = SimpleNamespace


def test_sort_status():
    # ソート前のステータス
    unsorted_status = (
        "🚋平常運転",
        "🕒列車遅延",
        "🛑運転見合わせ",
        "⚠️その他",
        "🚋運転再開",
        "ℹ️運転状況",
        "🗒️運転計画",
        "🚧交通障害情報",
        "ℹ️運転情報",
    )

    unsorted_trains = tuple(
        TrainStatus(train=f"線{i}", status=s, detail="")
        for i, s in enumerate(unsorted_status)
    )
    sorted_trains = sort_status(unsorted_trains)
    sorted_status = tuple(t.status for t in sorted_trains)

    correct_status = (
        "🛑運転見合わせ",
        "🕒列車遅延",
        "ℹ️運転情報",
        "ℹ️運転状況",
        "🗒️運転計画",
        "🚧交通障害情報",
        "🚋運転再開",
        "🚋平常運転",
        "⚠️その他",
    )

    assert sorted_status == correct_status
