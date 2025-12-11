import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any

import requests

from enums import Region
from utils.make_logger import make_logger

from ..trainstatus import TrainStatus


@dataclass
class TrainInfoResponse:
    is_success: bool
    data: tuple[TrainStatus, ...] | None
    error: str | None = None


class BaseTrainInfoClient(ABC):
    ROOT: str | None = None
    TRAININFO_ENDPOINT: str | None = None

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
    def _fetch(self) -> Any:
        """
        データを取得する。self.requestでラップするため、エラーハンドリングは不要。

        Returns
        -------
        any
            取得した生データ
        """
        pass

    @abstractmethod
    def _parse(self, raw: Any) -> tuple[TrainStatus, ...]:
        """
        生データを解析して tuple[TrainStatus, ...]を返す。

        Parameters
        ----------
        raw: dict[any]
            生データ

        Returns
        -------
        tuple[TrainStatus, ...]
            解析結果
        """
        pass

    def request(self) -> TrainInfoResponse:
        """
        データを取得する。エラーハンドリングを行い、TrainInfoResponseを返す。
        基本的に継承するだけでよい。変更が必要な場合はサブクラスでオーバーライド。

        Returns
        -------
        TrainInfoResponse
            取得結果
        """
        for i in range(self.retry_times):
            try:
                raw = self._fetch()
                return TrainInfoResponse(
                    is_success=True,
                    data=self._parse(raw),
                    error=None,
                )
            except JSONDecodeError as e:
                self.logger.error(f"JSON decode error. no retry: {e}")
                break
            except ValueError as e:
                self.logger.error(f"Value error while decoding JSON: {e}")
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

        return TrainInfoResponse(
            is_success=False,
            data=None,
            error="Failed to retrieve data after retries.",
        )

    def _status_exception_handler(
        self, status: int, e: requests.RequestException, i: int
    ) -> tuple[bool, float | None]:
        """
        ステータスコードに応じた例外処理を行う。
        基本的には継承するだけでよい。変更が必要な場合はサブクラスでオーバーライド。

        Parameters
        ----------
        status : int
            ステータスコード
        e : requests.RequestException
            発生した例外
        i : int
            現在のリトライ回数

        Returns
        -------
        tuple[bool, float | None]
            リトライ可否、リトライまでの遅延時間
        """
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
