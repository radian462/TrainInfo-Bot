from typing import NamedTuple

import requests

from enums import Region
from utils.make_logger import make_logger

from .sources.baseclient import BaseTrainInfoClient
from .sources.nhk import NHKClient
from .sources.yahoo import YahooClient
from .trainstatus import TrainStatus


class ClientsInfo(NamedTuple):
    client: BaseTrainInfoClient
    priority: int  # これは小さい順に処理されます。


class TrainInfoClient:
    def __init__(
        self,
        region: Region,
        proxy: dict[str, str] | None = None,
        timeout: int = 10,
        retry_sleep: float = 1.0,
        yahoo_app_id: str | None = None,
    ) -> None:
        self.region = region
        self.proxy = proxy
        self.timeout = timeout
        self.retry_sleep = retry_sleep

        self.logger = make_logger(type(self).__name__, context=region.label.upper())
        self.session = requests.Session()
        self.session.proxies = proxy

        self.yahoo_app_id = yahoo_app_id

        if not self.yahoo_app_id:
            self.logger.warning(
                "Yahoo APP ID is not provided. Sub source requests may fail."
            )

        self.clients: list[ClientsInfo] = [
            ClientsInfo(
                NHKClient(
                    session=self.session,
                    region=region,
                    timeout=timeout,
                    retry_sleep=retry_sleep,
                ),
                priority=1,
            )
        ]

        if self.yahoo_app_id:
            self.clients.append(
                ClientsInfo(
                    YahooClient(
                        session=self.session,
                        region=region,
                        timeout=timeout,
                        retry_sleep=retry_sleep,
                        yahoo_app_id=self.yahoo_app_id,
                    ),
                    priority=2,
                )
            )

    def request(self) -> tuple[TrainStatus, ...]:
        sorted_clients = sorted(self.clients, key=lambda x: x.priority)
        for client_info in sorted_clients:
            client = client_info.client
            result = client.request()
            if not result:
                self.logger.warning(
                    f"No data retrieved from source: {type(client).__name__}"
                )
                continue
            else:
                self.logger.info(
                    f"Succeeded in fetching data from {type(client).__name__}"
                )

            return result

        self.logger.error("All sources failed to retrieve data.")
        return ()
