import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from dotenv import load_dotenv

from enums import Region
from runner.manager import RegionalManager
from server.run import server_run
from utils.make_logger import clear_log_file, make_logger

logger = make_logger("Main")


def _calc_next_execute(interval: int, now: datetime | None = None) -> datetime:
    now = now or datetime.now()
    timestamp = int(now.timestamp())

    next_ts = (timestamp // interval + 1) * interval
    return datetime.fromtimestamp(next_ts)


def main():
    managers = [RegionalManager(region) for region in Region]
    interval = 600 if not DEBUG else 60  # seconds

    while True:
        next_execute = _calc_next_execute(interval=interval)
        now = datetime.now()
        sleep_sec = (next_execute - now).total_seconds()
        if sleep_sec > 0:
            logger.info(f"Sleep {int(sleep_sec)} seconds")
            logger.info(f"Next execution at {next_execute:%H:%M:%S}")
            time.sleep(sleep_sec)

        with ThreadPoolExecutor() as executor:
            executor.map(lambda m: m.execute(), managers)


if __name__ == "__main__":
    load_dotenv()
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    clear_log_file()
    server_run()
    main()
