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
