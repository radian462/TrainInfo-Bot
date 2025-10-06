from .normalizer import STATUS_EMOJI, status_normalizer
from .request import TrainStatus

ORDER_PRIORITY = {
    status_normalizer(key): i for i, (key, value) in enumerate(STATUS_EMOJI.items())
}


def sort_status(trains: tuple[TrainStatus, ...]) -> tuple[TrainStatus, ...]:
    return tuple(sorted(trains, key=lambda t: ORDER_PRIORITY.get(t.status, 999)))


def create_message(
    latest: tuple[TrainStatus, ...], previous: tuple[TrainStatus, ...], width: int = 300
) -> list[str] | None:
    if not latest or not previous:
        return None

    if latest == previous:
        return ["運行状況に変更はありません。"]

    latest = sort_status(latest)
    previous = sort_status(previous)

    previous_dict = {p.train: p for p in previous}
    incident_to_another = [
        l for l in latest if (p := previous_dict.get(l.train)) and l.status != p.status
    ]
    new_incidents = [l for l in latest if l.train not in previous_dict]
    resolved_incidents = [
        p
        for p in previous
        if p.train not in {l.train for l in latest} and p.status != "🚋平常運転"
    ]
    unchanged_incidents = [
        l
        for l in latest
        if (p := previous_dict.get(l.train)) and l.status == p.status != "🚋平常運転"
    ]

    messages = []
    for r in incident_to_another:
        messages.append(
            f"{r.train} : {previous_dict[r.train].status}➡️{r.status}\n{r.detail}"
        )

    for r in new_incidents:
        messages.append(f"{r.train} : 🚋平常運転➡️{r.status}\n{r.detail}")

    for r in resolved_incidents:
        messages.append(f"{r.train} : {r.status}➡️🚋平常運転\n{r.detail}")

    for r in unchanged_incidents:
        messages.append(f"{r.train} : {r.status}\n{r.detail}")

    if not messages:
        return None

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
