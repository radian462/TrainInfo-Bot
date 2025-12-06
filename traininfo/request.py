from dataclasses import dataclass

import requests

from enums import Region
from utils.make_logger import make_logger

from .sources.baseclient import BaseTrainInfoClient, TrainInfoResponse
from .sources.nhk import NHKClient
from .sources.yahoo import YahooClient


@dataclass
class ClientsInfo:
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
        """
        複数の情報源から運行情報を取得するクライアント
        Parameters
        ----------
        region : Region
            運行情報を取得する地域。
        proxy : dict[str, str] | None, optional
            プロキシ設定。デフォルトはNone。
        timeout : int, optional
            リクエストのタイムアウト時間（秒）。デフォルトは10秒。
        retry_sleep : float, optional
            リトライ時の待機時間（秒）。デフォルトは1.0秒。
        yahoo_app_id : str | None, optional
            Yahoo APIのアプリケーションID。デフォルトはNone。
        """

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

    def request(self) -> TrainInfoResponse:
        """
        運行情報を取得する。
        登録されたクライアントを優先度順に試行し、最初に成功したものを返す。
        すべてのクライアントが失敗した場合は、失敗のレスポンスを返す。

        Returns
        -------
        TrainInfoResponse
            運行情報のレスポンス。
        """
        sorted_clients = sorted(self.clients, key=lambda x: x.priority)
        for client_info in sorted_clients:
            client = client_info.client
            result = client.request()
            if not result.is_success:
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
        return TrainInfoResponse(
            is_success=False,
            data=None,
            error="All sources failed to retrieve data.",
        )
