from utils.make_logger import make_logger

from .normalizer import STATUS_EMOJI, status_normalizer
from .trainstatus import TrainStatus

logger = make_logger("message")

DEFAULT_MESSAGE = "現在、ほぼ平常通り運転しています。"
ORDER_PRIORITY = {
    status_normalizer(key): i for i, (key, value) in enumerate(STATUS_EMOJI.items())
}


def sort_status(trains: tuple[TrainStatus, ...]) -> tuple[TrainStatus, ...]:
    return tuple(sorted(trains, key=lambda t: ORDER_PRIORITY.get(t.status, 999)))


def create_message(
    latest: tuple[TrainStatus, ...], previous: tuple[TrainStatus, ...], width: int = 300
) -> list[str]:
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
