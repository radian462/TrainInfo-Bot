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
        self.clients: list[ClientsInfo] = []

        self.yahoo_app_id = yahoo_app_id

        if not self.yahoo_app_id:
            self.logger.warning(
                "Yahoo APP ID is not provided. Sub source requests may fail."
            )

        self._register_clients()

    def _register_clients(self) -> None:
        """
        クラスに利用可能なクライアントを登録する。
        クライアントは優先度と共に登録される。
        """
        # クライアントと優先度を設定。
        _CLIENTS = ((NHKClient, 1), (YahooClient, 2))

        for client, priority in _CLIENTS:
            args = {
                "region": self.region,
                "session": self.session,
                "timeout": self.timeout,
                "retry_sleep": self.retry_sleep,
            }

            if client is YahooClient:
                if self.yahoo_app_id:
                    args["yahoo_app_id"] = self.yahoo_app_id
                else:
                    self.logger.warning(
                        "Skipping YahooClient registration due to missing APP ID."
                    )
                    continue

            instance = client(**args)
            self.clients.append(ClientsInfo(client=instance, priority=priority))

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


if __name__ == "__main__":
    import os

    import dotenv

    dotenv.load_dotenv()
    client = TrainInfoClient(
        region=Region.KANTO, yahoo_app_id=os.getenv("YAHOO_APP_ID")
    )
    response = client.request()
    if response.is_success:
        print(response.data)
    else:
        print(f"Error fetching data: {response.error}")
