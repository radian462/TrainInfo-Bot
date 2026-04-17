from typing import Final

import yaml

with open("./traininfo/status.yaml", "r") as f:
    data = yaml.safe_load(f) or {}
    statuses = data.get("statuses", {})
    STATUS_EMOJI: Final[dict[str, str]] = {
        item["label"]: item.get("emoji", "")
        for item in statuses.values()
        if item.get("label")
    }


def NHK_status_converter(code: str) -> str:
    """
    NHKの運行状況コードを運行状況に変換する。

    Parameters
    ----------
    code : str
        NHKの運行状況コード。

    Returns
    -------
    str
        運行状況。
    """
    nhk_to_label = {
        code: v["label"] for v in statuses.values() for code in v.get("NHK_code", [])
    }
    return nhk_to_label.get(code, "その他")


def add_emoji_prefix(status: str) -> str:
    """
    絵文字を運行状況の前に付与する。
    先頭に絵文字を付与して返す。運行状況が部分一致する場合も対応する。

    Parameters
    ----------
    status : str
        絵文字を付与する運行状況。

    Returns
    -------
    str
        絵文字を付与した運行状況。
    """
    for key in STATUS_EMOJI.keys():
        if key in status:
            return STATUS_EMOJI[key] + key
    return "⚠️その他"


def status_normalizer(status: str | None = None, NHK_code: str | None = None) -> str:
    """
    運行状況を正規化する。
    運行状況は先頭に絵文字を付与して返す。運行状況が部分一致する場合も対応する。
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
    if NHK_code:
        status = NHK_status_converter(NHK_code)
    if status:
        return add_emoji_prefix(status)
    return "⚠️その他"
