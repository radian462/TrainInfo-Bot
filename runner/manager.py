import os
from threading import Thread

from clients.bluesky import BlueskyClient
from clients.misskeyio import MisskeyIOClient
from enums import AuthType, Region, Service
from traininfo.database import get_previous_status, set_latest_status
from traininfo.message import create_message
from traininfo.request import TrainInfoClient
from traininfo.trainstatus import TrainStatus
from utils.make_logger import make_logger


class RegionalManager:
    """
    各地域ごとの投稿管理を行うクラス

    Attributes
    ----------
    region : Region
        管理対象の地域
    traininfo_client : TrainInfoClient
        運行情報取得クライアント
    logger : Logger
        ロガー
    clients : list[BlueskyClient | MisskeyIOClient]
        各サービスのクライアントリスト

    Methods
    -------
    login_all() -> bool
        すべてのクライアントでログインを試みる
    get_auth(service: Service, auth_type: AuthType) -> tuple[str, ...] | None
        指定されたサービスと認証タイプに基づいて認証情報を取得する
    get_table_name() -> str | None
        データベースのテーブル名を取得する
    execute() -> None
        運行情報の取得、メッセージの生成、投稿を実行する
    """

    def __init__(self, region: Region):
        self.region = region
        self.traininfo_client = TrainInfoClient(
            region, yahoo_app_id=os.getenv("YAHOO_APP_ID")
        )
        self.logger = make_logger(type(self).__name__, context=region.label.upper())
        self.clients = [service.client(region.label.upper()) for service in Service]

        self.login_all()

    def login_all(self) -> bool:
        """
        すべてのクライアントでログインを試みる

        Returns
        -------
        bool
            すべてのクライアントが正常にログインできた場合はTrue、そうでない場合はFalse
        """
        is_succeed = [
            client.login(*self.get_auth(service, client.auth_type))
            for service, client in zip(Service, self.clients)
        ]
        if all(is_succeed):
            self.logger.info(f"All clients logged in for {self.region.label}")
            return True
        else:
            self.logger.error(f"Some clients failed to log in for {self.region.label}")
            return False

    def get_auth(self, service: Service, auth_type: AuthType) -> tuple[str, ...] | None:
        """
        指定されたサービスと認証タイプに基づいて認証情報を取得する

        Parameters
        ----------
        service : Service
            認証情報を取得するサービス
        auth_type : AuthType
            認証タイプ（USERNAME_PASSWORDまたはTOKEN）

        Returns
        -------
        tuple[str, ...] | None
            認証情報のタプル、または認証情報が見つからない場合はNone
        """
        service_name = service.label.upper()
        region = self.region.label.upper()
        if auth_type == AuthType.USERNAME_PASSWORD:
            username = os.getenv(f"{service_name}_{region}_NAME")
            password = os.getenv(f"{service_name}_{region}_PASS")

            if not username or not password:
                self.logger.error(
                    f"Bluesky credentials not set for {self.region.label}"
                )
                return None

            return username, password
        elif auth_type == AuthType.TOKEN:
            token = os.getenv(f"{service_name}_{region}_TOKEN")

            if not token:
                self.logger.error(f"Misskey token not set for {self.region.label}")
                return None

            return (token,)

    def get_table_name(self) -> str | None:
        """
        データベースのテーブル名を取得する

        Returns
        -------
        str | None
            テーブル名、またはテーブル名が見つからない場合はNone
        """
        table_name = os.getenv(f"{self.region.label.upper()}_DB")

        if not table_name:
            self.logger.error(f"DB name not set for {self.region.label}")
            return None

        return table_name

    def execute(self) -> None:
        """
        運行情報の取得、メッセージの生成、投稿を実行する
        """

        def post(
            client: BlueskyClient | MisskeyIOClient,
            data: tuple[TrainStatus, ...],
            previous: tuple[TrainStatus, ...],
        ) -> None:
            messages = create_message(data, previous, width=client.post_string_limit)
            post = None
            for i, message in enumerate(messages):
                try:
                    post = client.post(message, post.ref if post and post.ref else None)
                    if post.success:
                        self.logger.info(
                            f"Completed posting to {client.service_name} {i + 1}/{len(messages)}"
                        )
                    else:
                        self.logger.warning(
                            f"Failed to post message to {client.service_name} {i + 1}/{len(messages)}"
                        )
                except Exception:
                    self.logger.error("Failed to post message", exc_info=True)

        result = self.traininfo_client.request()
        if not result.data and result.is_success:
            self.logger.info("No data retrieved from TrainInfoClient")
            return
        data = result.data if result.data else tuple()
        table_name = self.get_table_name()

        try:
            if table_name is not None:
                previous = get_previous_status(table_name)
            else:
                raise RuntimeError("table name is None")
        except Exception:
            self.logger.error("Failed to get previous data", exc_info=True)
            previous = tuple()

        messages = create_message(data, previous)
        if messages == ["運行状況に変更はありません。"]:
            self.logger.info("No changes in train status")
            return

        try:
            if table_name is not None:
                set_latest_status(table_name, list(data))
            else:
                raise RuntimeError("table name is None")
        except Exception:
            self.logger.error("Failed to save data", exc_info=True)

        threads = [
            Thread(target=post, args=(client, data, previous))
            for client in self.clients
        ]
        for t in threads:
            t.start()

        for t in threads:
            t.join()
