import time
from abc import ABC, abstractmethod
from json import JSONDecodeError

import requests

from enums import Region
from utils.make_logger import make_logger

from ..trainstatus import TrainStatus


class BaseTrainInfoClient(ABC):
    def __init__(
        self,
        session: requests.Session,
        region: Region,
        timeout: int = 10,
        retry_sleep: float = 1.0,
        retry_times: int = 3,
    ):
        self.logger = make_logger(type(self).__name__, context=region.label)
        self.session = session
        self.region = region
        self.timeout = timeout
        self.retry_sleep = retry_sleep
        self.retry_times = retry_times

    @abstractmethod
    def _fetch(self) -> tuple[TrainStatus, ...]:
        pass

    @abstractmethod
    def _parse(self, r: requests.Response) -> tuple[TrainStatus, ...]:
        pass

    def request(self) -> tuple[TrainStatus, ...]:
        for i in range(self.retry_times):
            try:
                return self._fetch()
            except JSONDecodeError as e:
                self.logger.error(f"JSON decode error. no retry: {e}")
                break
            except requests.Timeout as e:
                self.logger.warning(f"Request timed out: {e}")
            except requests.RequestException as e:
                if hasattr(e, "response") and e.response is not None:
                    status = e.response.status_code
                else:
                    raise e

                is_retry, delay = self._status_exception_handler(status, e, i)

                if not is_retry:
                    break

                if delay:
                    self.logger.info(f"Retrying... ({i + 1}/{self.retry_times})")
                    time.sleep(delay)
                    continue
            except Exception as e:
                self.logger.error(f"Error requesting: {e}")

            if i < self.retry_times - 1:
                self.logger.info(f"Retrying... ({i + 1}/{self.retry_times})")
                time.sleep(self.retry_sleep)
                continue

        return ()

    def _status_exception_handler(
        self, status: int, e: requests.RequestException, i: int
    ) -> tuple[bool, float | None]:
        match status:
            case 429:
                retry_after = e.response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    delay = float(retry_after)
                else:
                    delay = 2**i
                self.logger.warning(f"Rate limited. Retrying after {delay}s...")
                return (True, delay)
            case _ if status >= 500:
                self.logger.warning(
                    f"Server error ({status}). retrying... ({i + 1}/{self.retry_times}): {e}"
                )
                return (True, None)
            case _:
                self.logger.error(f"Client error occurred while requesting: {e}")
                return (False, None)
