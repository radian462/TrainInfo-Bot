from dataclasses import dataclass

import requests

from enums import Region
from helpers.make_logger import make_logger

from .normalizer import status_normalizer


@dataclass(frozen=True)
class TrainStatus:
    train: str
    status: str
    detail: str


class TrainInfoClient:
    def __init__(
        self,
        region: Region,
        proxy: dict[str, str] | None,
        timeout: int = 10,
        yahoo_app_id: str | None = None,
    ) -> None:
        self.region = region
        self.proxy = proxy
        self.timeout = timeout

        self.logger = make_logger(type(self).__name__, context=region.label.upper())
        self.session = requests.Session()
        self.session.proxies = proxy

        self.yahoo_app_id = yahoo_app_id
        self.NHK_ENDPOINT = (
            "https://www.nhk.or.jp/n-data/traffic/train/traininfo_area_0%s.json"
        )
        self.YAHOO_ENDPOINT = (
            "https://cache-diainfo-transit.yahooapis.jp/v4/diainfo/train"
        )

        if not self.yahoo_app_id:
            self.logger.warning(
                "Yahoo APP ID is not provided. Sub source requests may fail."
            )

    def request(self) -> tuple[TrainStatus]:
        result = self._request_from_NHK()
        if not result:
            self.logger.warning("No data from NHK, trying Yahoo...")
            result = self._request_from_yahoo()

            if not result:
                self.logger.error("No data received from all sources.")
                return tuple()

        return result

    def _request_from_NHK(self, retry_times: int = 3) -> tuple[TrainStatus]:
        for i in range(retry_times):
            try:
                response = self.session.get(
                    self.NHK_ENDPOINT % self.region.value,
                    timeout=self.timeout,
                )

                response.raise_for_status()
                original_data = response.json().get("channel", {}).get(
                    "item"
                ) + response.json().get("channel", {}).get("itemLong")
                return tuple(
                    TrainStatus(
                        train=o.get("trainLine", ""),
                        status=status_normalizer(o.get("status", "")),
                        detail=o.get("textLong", ""),
                    )
                    for o in original_data
                )
            except Exception as e:
                self.logger.error(f"Error requesting from NHK: {e}")
                if i < retry_times - 1:
                    self.logger.info(f"Retrying... ({i + 1}/{retry_times})")
                    return tuple()

    def _request_from_yahoo(self, retry_times: int = 3) -> tuple[TrainStatus]:
        pass
