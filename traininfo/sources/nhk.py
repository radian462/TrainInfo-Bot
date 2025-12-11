from typing import Any

import requests

from enums import Region

from ..normalizer import status_normalizer
from ..trainstatus import TrainStatus
from .baseclient import BaseTrainInfoClient


class NHKClient(BaseTrainInfoClient):
    ROOT = "https://www.nhk.or.jp"
    TRAININFO_ENDPOINT = "/n-data/traffic/train/traininfo_area_0{}.json"

    def __init__(
        self,
        session: requests.Session,
        region: Region,
        timeout: int = 10,
        retry_sleep: float = 1.0,
        retry_times: int = 3,
    ):
        super().__init__(
            session=session,
            region=region,
            timeout=timeout,
            retry_sleep=retry_sleep,
            retry_times=retry_times,
        )

    def _fetch(self) -> Any:
        r = self.session.get(
            self.ROOT + self.TRAININFO_ENDPOINT.format(self.region.id),
            timeout=self.timeout,
        )
        r.raise_for_status()

        return r.json()

    def _parse(self, raw: Any) -> tuple[TrainStatus, ...]:
        channel = raw.get("channel", {})
        original_data = channel.get("item", []) + channel.get("itemLong", [])

        return tuple(
            TrainStatus(
                train=o.get("trainLine", ""),
                status=status_normalizer(o.get("status", "")),
                detail=o.get("textLong", ""),
            )
            for o in original_data
            if isinstance(o, dict)
        )
