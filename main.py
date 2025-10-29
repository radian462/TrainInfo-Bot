import os
import time
from datetime import datetime
from enum import Enum
from threading import Thread

from dotenv import load_dotenv

from Modules.Clients.bluesky import BlueskyClient
from Modules.Clients.misskeyio import MisskeyIOClient
from Modules.healthcheck import healthcheck
from Modules.make_logger import make_logger
from Modules.traininfo.database import get_previous_status, set_latest_status
from Modules.traininfo.message import create_message
from Modules.traininfo.request import TrainStatus, request_from_NHK, request_from_yahoo

healthcheck()
load_dotenv()
logger = make_logger("main")

DEBUG = os.getenv("DEBUG", "False").lower() == "true"


class Region(Enum):
    KANTO = ("kanto", 4)
    KANSAI = ("kansai", 6)

    def __init__(self, name: str, region_id: int):
        self._name_str = name
        self._region_id = region_id

    @property
    def id(self):
        return self._region_id

    @property
    def label(self):
        return self._name_str


class Service(Enum):
    BLUESKY = ("Bluesky", BlueskyClient)
    MISSKEYIO = ("MisskeyIO", MisskeyIOClient)

    @property
    def label(self):
        return self.value[0]

    @property
    def client(self):
        return self.value[1]


class RegionalManager:
    def __init__(self, region: Region):
        self.region = region
        self.logger = make_logger("RegionalManager", context=region.label)
        self.clients = [service.client() for service in Service]

        self.login_all()

    def login_all(self) -> bool:
        is_succeed = [
            client.login(self.get_auth(service))
            for service, client in zip(Service, self.clients)
        ]
        if all(is_succeed):
            self.logger.info(f"All clients logged in for {self.region.label}")
            return True
        else:
            self.logger.error(f"Some clients failed to log in for {self.region.label}")
            return False

    def get_auth(self, service: Service) -> tuple[str, str] | None:
        service_name = service.label.upper()
        region = self.region.label.upper()
        username = os.getenv(f"{service_name}_{region}_NAME")
        password = os.getenv(f"{service_name}_{region}_PASS")

        if not username or not password:
            self.logger.error(f"Bluesky credentials not set for {self.region.label}")
            return None

        return username, password

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
                    self.logger.info(
                        f"Completed posting to {client.service_name} {i + 1}/{len(messages)}"
                    )
                except Exception:
                    self.logger.error("Failed to post message", exc_info=True)

        try:
            data = request_from_NHK(self.region.id)
            if data is None:
                self.logger.warning("No data from NHK, trying Yahoo...")
                data = request_from_yahoo(self.region.id)
                if data is not None:
                    self.logger.info("Data received from Yahoo")
                else:
                    self.logger.error("No data received from both NHK and Yahoo")
                    return
            else:
                self.logger.info("Data received from NHK")
        except Exception:
            self.logger.error("Failed to get data", exc_info=True)
            return

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

        self.logger.info(f"All posts completed for {self.region.label}")


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
    main()
