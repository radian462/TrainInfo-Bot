import os
import time
from datetime import datetime
from enum import Enum
from threading import ThreadPoolExecutor

import schedule
from dotenv import load_dotenv

from Modules.Clients.bluesky import Bluesky
from Modules.healthcheck import healthcheck
from Modules.make_logger import make_logger
from Modules.traininfo.database import (TrainStatus, get_previous_status,
                                        set_latest_status)
from Modules.traininfo.message import create_message
from Modules.traininfo.request import request_from_NHK, request_from_yahoo

healthcheck()
load_dotenv()
logger = make_logger("main")


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
    BLUESKY = "BlueSky"


class BlueskyManager:
    def __init__(
        self,
        region: Region,
    ):
        self.logger = make_logger(f"BlueSky[{region.label}]")
        self.region = region

        self.bluesky = Bluesky()
        self.bluesky.login(*self.get_auth())

        self.logger.info("Logged in Bluesky")

    def get_auth(self) -> tuple[str, str]:
        return (
            os.getenv(f"BLUESKY_{self.region.label.upper()}_NAME"),
            os.getenv(f"BLUESKY_{self.region.label.upper()}_PASS"),
        )

    def get_table_name(self) -> str:
        return os.getenv(f"{self.region.label.upper()}_DB")

    def execute(self) -> None:
        try:
            data = request_from_NHK(self.region.id)
            if data is None:
                self.logger.warning("No data from NHK, try Yahoo")
                data = request_from_yahoo(self.region.id)
        except Exception as e:
            self.logger.error(f"Failed to get data", exc_info=True)
            return

        if data is None:
            self.logger.error("No data received from both NHK and Yahoo")
            return

        try:
            previous = get_previous_status(self.get_table_name())
        except Exception as e:
            self.logger.error(f"Failed to get previous data", exc_info=True)
            previous = tuple()

        try:
            set_latest_status(self.get_table_name(), data)
        except Exception as e:
            self.logger.error(f"Failed to save data", exc_info=True)

        messages = create_message(data, previous)
        if messages == ["運行状況に変更はありません。"]:
            self.logger.info("No changes in train status")
            return

        for i, message in enumerate(messages):
            try:
                self.bluesky.post_status(message, visibility="public")
                self.logger.info(f"Completed to post {i+1}/{len(messages)}")
            except Exception as e:
                self.logger.error(f"Failed to post message", exc_info=True)

        self.logger.info("Done all posts")


class ServiceManager:
    def __init__(
        self,
        service: Service,
        region: Region,
    ):
        self.service = service
        self.region = region

        match self.service:
            case Service.BLUESKY:
                self.manager = BlueskyManager(region)
            case _:
                raise ValueError("Unsupported service")

    def execute(self) -> None:
        self.manager.execute()


def main():
    managers = [ServiceManager(Service.BLUESKY, region) for region in Region]

    def job():
        logger.info("Starting scheduled job...")
        with ThreadPoolExecutor(max_workers=len(managers)) as executor:
            executor.map(lambda m: m.execute(), managers)

    interval = 10
    schedule.every(interval).minutes.do(job)
    logger.info(f"Scheduler started, running every {interval} minutes")

    while True:
        schedule.run_pending()
        time.sleep(1)



if __name__ == "__main__":
    main()
