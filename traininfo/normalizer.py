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
    """
    運行状況を正規化する。
    先頭に絵文字を付与して返す。運行状況が部分一致する場合も対応する。
    対応する運行状況がない場合は「⚠️その他」を返す。

    Parameters
    ----------
    status : str
        正規化する運行状況。

    Returns
    -------
    str
        正規化された運行状況。
    """
    for key in STATUS_EMOJI.keys():
        if key in status:
            return STATUS_EMOJI[key] + key
    return "⚠️その他"
