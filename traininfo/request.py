from dataclasses import dataclass

import requests

from enums import Region
from helpers.make_logger import make_logger


@dataclass(frozen=True)
class TrainStatus:
    train: str
    status: str
    detail: str


class TrainInfoClient:
    def __init__(self, region: Region, yahoo_app_id: str | None = None) -> None:
        self.region = region
        self.yahoo_app_id = yahoo_app_id

        self.logger = make_logger(type(self).__name__, context=region.label.upper())
        self.session = requests.Session()

        if not self.yahoo_app_id:
            self.logger.warning(
                "Yahoo APP ID is not provided. Sub source requests may fail."
            )

    def request(self) -> tuple[TrainStatus]:
        pass

    def _request_from_NHK(self) -> tuple[TrainStatus]:
        pass

    def _request_from_yahoo(self) -> tuple[TrainStatus]:
        pass
