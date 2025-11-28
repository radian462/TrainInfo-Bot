import os
import time
from datetime import datetime
from threading import Thread

import dotenv

from clients.baseclient import AuthType
from clients.bluesky import BlueskyClient
from clients.misskeyio import MisskeyIOClient
from enums import Region, Service
from traininfo.database import get_previous_status, set_latest_status
from traininfo.message import create_message
from traininfo.request import TrainInfoClient
from traininfo.trainstatus import TrainStatus
from utils.make_logger import clear_log_file, make_logger
from utils.server.run import server_run

logger = make_logger("main")


class RegionalManager:
    def __init__(self, region: Region):
        self.region = region
        self.traininfo_client = TrainInfoClient(
            region, yahoo_app_id=os.getenv("YAHOO_APP_ID")
        )
        self.logger = make_logger(type(self).__name__, context=region.label.upper())
        self.clients = [service.client(region.label.upper()) for service in Service]

        self.login_all()

    def login_all(self) -> bool:
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
        table_name = os.getenv(f"{self.region.label.upper()}_DB")

        if not table_name:
            self.logger.error(f"DB name not set for {self.region.label}")
            return None

        return table_name

    def execute(self) -> None:
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


def main():
    managers = [RegionalManager(region) for region in Region]

    interval = 10 if not DEBUG else 1
    while True:
        minutes, seconds = datetime.now().minute, datetime.now().second

        threads = []
        if minutes % interval == 0:
            threads = [Thread(target=manager.execute) for manager in managers]
            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

        next_minute = (minutes // interval + 1) * interval
        wait_time = (next_minute - minutes) * 60 - seconds
        logger.info(f"Sleep {wait_time} seconds")
        logger.info(f"Next execution at {next_minute:02d}:00")
        time.sleep(wait_time)


if __name__ == "__main__":
    dotenv.load_dotenv()
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    clear_log_file()
    server_run()
    main()
