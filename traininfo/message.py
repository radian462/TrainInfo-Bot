from pathlib import Path
from typing import Final

import yaml

from utils.make_logger import make_logger

from .normalizer import status_normalizer
from .trainstatus import TrainStatus

logger = make_logger("message")

DEFAULT_MESSAGE = "現在、ほぼ平常通り運転しています。"
with open(Path(__file__).parent / "status.yaml", "r") as f:
    data = yaml.safe_load(f) or {}
    statuses = data.get("statuses", {})
    ORDER_PRIORITY: Final[dict[str, int]] = {
        status_normalizer(item["label"]): item.get("priority", 999)
        for item in statuses.values()
        if item.get("label")
    }


def sort_status(trains: tuple[TrainStatus, ...]) -> tuple[TrainStatus, ...]:
    """
    運行状況を優先度順にソートする。

    Parameters
    ----------
    trains : tuple[TrainStatus, ...]
        ソートする運行状況のタプル。

    Returns
    -------
    tuple[TrainStatus, ...]
        ソートされた運行状況のタプル。
    """
    return tuple(sorted(trains, key=lambda t: ORDER_PRIORITY.get(t.status, 999)))


def create_message(
    latest: tuple[TrainStatus, ...], previous: tuple[TrainStatus, ...], width: int = 300
) -> list[str]:
    """
    運行状況の変化に基づいてメッセージを作成する。
    運行状況は優先度順にソートされ、変更点、新規、解決済み、変化なしの順にメッセージが生成される。
    変化がない場合は「運行状況に変更はありません。」というメッセージを返す。

    Parameters
    ----------
    latest : tuple[TrainStatus, ...]
        最新の運行状況のタプル。
    previous : tuple[TrainStatus, ...]
        前回の運行状況のタプル。
    width : int, optional
        メッセージの最大幅。デフォルトは300。

    Returns
    -------
    list[str]
        作成されたメッセージのリスト。
    """
    latest = sort_status(latest)
    previous = sort_status(previous)

    previous_dict = {p.train: p for p in previous}
    incident_to_another = [
        ts
        for ts in latest
        if (p := previous_dict.get(ts.train)) and ts.status != p.status
    ]
    new_incidents = [ts for ts in latest if ts.train not in previous_dict]
    resolved_incidents = [
        ts
        for ts in previous
        if ts.train not in {ts.train for ts in latest} and ts.status != "🚋平常運転"
    ]
    unchanged_incidents = [
        ts
        for ts in latest
        if (p := previous_dict.get(ts.train)) and ts.status == p.status != "🚋平常運転"
    ]

    if not new_incidents and not incident_to_another and not resolved_incidents:
        return ["運行状況に変更はありません。"]

    messages = []

    for r in incident_to_another:
        prev = previous_dict[r.train]
        messages.append(f"{r.train} : {prev.status}➡️{r.status}\n{r.detail}")

    for r in new_incidents:
        messages.append(f"{r.train} : 🚋平常運転➡️{r.status}\n{r.detail}")

    for r in resolved_incidents:
        messages.append(f"{r.train} : {r.status}➡️🚋平常運転\n{DEFAULT_MESSAGE}")

    for r in unchanged_incidents:
        messages.append(f"{r.train} : {r.status}\n{r.detail}")

    if not messages:
        logger.info("No changes detected after processing.")
        return []

    splited_messages = []
    temp_message = ""
    for m in messages:
        if len(temp_message + m + "\n\n") <= width:
            temp_message += m + "\n\n"
        else:
            if temp_message.strip():
                splited_messages.append(temp_message.strip())
                temp_message = m + "\n\n"

    if temp_message.strip():
        splited_messages.append(temp_message.strip())

    return splited_messages
