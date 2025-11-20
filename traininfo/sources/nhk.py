import requests

from enums import Region

from ..normalizer import status_normalizer
from ..trainstatus import TrainStatus
from .baseclient import BaseTrainInfoClient


class NHKClient(BaseTrainInfoClient):
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
        self.NHK_ENDPOINT = (
            "https://www.nhk.or.jp/n-data/traffic/train/traininfo_area_0%s.json"
        )

    def _fetch(self) -> tuple[TrainStatus, ...]:
        r = self.session.get(
            self.NHK_ENDPOINT % self.region.id,
            timeout=self.timeout,
        )
        r.raise_for_status()

        data = r.json()
        original_data = data.get("channel", {}).get("item", []) + data.get(
            "channel", {}
        ).get("itemLong", [])

        return tuple(
            TrainStatus(
                train=o.get("trainLine", ""),
                status=status_normalizer(o.get("status", "")),
                detail=o.get("textLong", ""),
            )
            for o in original_data
            if isinstance(o, dict)
        )
