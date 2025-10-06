from enum import Enum
import os
import time
from datetime import datetime
from threading import Thread

from dotenv import load_dotenv

from Modules.Clients.bluesky import Bluesky
from Modules.healthcheck import healthcheck
from Modules.make_logger import make_logger
from Modules.traininfo import TrainInfo

healthcheck()
load_dotenv()
logger = make_logger("main")


class Region(Enum):
    KANTO = "kanto"
    KANSAI = "kansai"


class Service(Enum):
    BLUESKY = "BlueSky"


class BlueskyManager:
    def __init__(
        self,
        region: Region,
    ):
        self.logger = make_logger(f"BlueSky[{region.value}]")

        self.region = region
        self.train_info = TrainInfo(region)

        self.bluesky = Bluesky()
        self.bluesky.login(*self.get_auth())

        self.logger.info("Logged in Bluesky")

    def get_auth(self) -> tuple[str, str]:
        return (
            os.getenv(f"BLUESKY_{self.region.value.upper()}_NAME"),
            os.getenv(f"BLUESKY_{self.region.value.upper()}_PASS"),
        )

    def bluesky_execute(self, messages: list[str]) -> None:
        post = None
        if messages == ["運行状況に変更はありません。"]:
            self.logger.info("Pending for the same post")
        else:
            for i, m in enumerate(messages):
                post = self.bluesky.post(m, post)
                self.logger.info(f"Successfully posted to Bluesky {i + 1}")

            self.logger.info("Done with posted")

    def execute(self) -> None:
        data = self.train_info.request()
        messages = self.train_info.make_message(data)
        self.bluesky_execute(messages)


class RegionalManager:
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
    managers = [RegionalManager(Service.BLUESKY, region) for region in Region]

    interval = 10
    while True:
        minutes, seconds = datetime.now().minute, datetime.now().second

        threads = []
        if minutes % interval == 0:
            threads = [Thread(target=manager.execute) for manager in managers]
            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            threads = []

        next_minute = (minutes // interval + 1) * interval
        wait_time = (next_minute - minutes) * 60 - seconds
        logger.info(f"Sleep {wait_time} seconds")
        time.sleep(wait_time)


if __name__ == "__main__":
    main()
