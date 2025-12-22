import os
import time
from datetime import datetime
from threading import Thread

from dotenv import load_dotenv

from enums import Region
from runner.manager import RegionalManager
from server.run import server_run
from utils.make_logger import clear_log_file, make_logger

logger = make_logger("Main")


def main():
    managers = [RegionalManager(region) for region in Region]

    interval = 10 if not DEBUG else 1
    while True:
        minutes, seconds = datetime.now().minute, datetime.now().second

        threads = []
        if minutes % interval == 0:
            threads = [Thread(target=m.execute) for m in managers]
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
    load_dotenv()
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    clear_log_file()
    server_run()
    main()
