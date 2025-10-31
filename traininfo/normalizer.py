from typing import Final

STATUS_EMOJI: Final[dict] = {
    "運転見合わせ": "🛑",
    "列車遅延": "🕒",
    "運転情報": "ℹ️",
    "運転状況": "ℹ️",
    "運転計画": "🗒️",
    "交通障害情報": "🚧",
    "運転再開": "🚋",
    "平常運転": "🚋",
    "その他": "⚠️",
}


def status_normalizer(status: str) -> str:
    for key in STATUS_EMOJI.keys():
        if key in status:
            return STATUS_EMOJI[key] + key
    return "⚠️その他"
