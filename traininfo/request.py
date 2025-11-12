import time
from dataclasses import dataclass
from json import JSONDecodeError

import requests

from enums import Region
from helpers.make_logger import make_logger

from .normalizer import status_normalizer


@dataclass(frozen=True)
class TrainStatus:
    train: str
    status: str
    detail: str


class TrainInfoClient:
    def __init__(
        self,
        region: Region,
        proxy: dict[str, str] | None,
        timeout: int = 10,
        retry_sleep: float = 1.0,
        yahoo_app_id: str | None = None,
    ) -> None:
        self.region = region
        self.proxy = proxy
        self.timeout = timeout
        self.retry_sleep = retry_sleep

        self.logger = make_logger(type(self).__name__, context=region.label.upper())
        self.session = requests.Session()
        self.session.proxies = proxy

        self.yahoo_app_id = yahoo_app_id
        self.NHK_ENDPOINT = (
            "https://www.nhk.or.jp/n-data/traffic/train/traininfo_area_0%s.json"
        )
        self.YAHOO_ENDPOINT = (
            "https://cache-diainfo-transit.yahooapis.jp/v4/diainfo/train"
        )

        if not self.yahoo_app_id:
            self.logger.warning(
                "Yahoo APP ID is not provided. Sub source requests may fail."
            )

    def request(self) -> tuple[TrainStatus]:
        result = self._request_from_NHK()
        if not result:
            self.logger.warning("No data from NHK, trying Yahoo...")
            result = self._request_from_yahoo()

            if not result:
                self.logger.error("No data received from all sources.")
                return ()

        return result

    def _request_from_NHK(self, retry_times: int = 3) -> tuple[TrainStatus]:
        for i in range(retry_times):
            try:
                r = self.session.get(
                    self.NHK_ENDPOINT % self.region.id,
                    timeout=self.timeout,
                )

                r.raise_for_status()
                original_data = r.json().get("channel", {}).get(
                    "item", []
                ) + r.json().get("channel", {}).get("itemLong", [])
                return tuple(
                    TrainStatus(
                        train=o.get("trainLine", ""),
                        status=status_normalizer(o.get("status", "")),
                        detail=o.get("textLong", ""),
                    )
                    for o in original_data
                    if isinstance(o, dict)
                )
            except JSONDecodeError as e:
                self.logger.error(f"JSON decode error from NHK. no retry: {e}")
                break
            except requests.Timeout as e:
                self.logger.warning(f"Request to NHK timed out: {e}")
            except requests.RequestException as e:
                if hasattr(e, "response") and e.response is not None:
                    status = e.response.status_code
                    if status == 429:
                        retry_after = e.response.headers.get("Retry-After")
                        if retry_after and retry_after.isdigit():
                            delay = float(retry_after)
                        else:
                            delay = 2**i
                        self.logger.warning(f"Rate limited. Retrying after {delay}s...")
                        time.sleep(delay)
                        continue
                    elif status >= 500:
                        self.logger.warning(
                            f"Server error ({status}). retrying... ({i + 1}/{retry_times}): {e}"
                        )
                    else:
                        self.logger.error(
                            f"Client error occurred while requesting NHK: {e}"
                        )
                        break
            except Exception as e:
                self.logger.error(f"Error requesting from NHK: {e}")

            if i < retry_times - 1:
                self.logger.info(f"Retrying... ({i + 1}/{retry_times})")
                time.sleep(self.retry_sleep)
                continue

        return ()

    def _request_from_yahoo(self, retry_times: int = 3) -> tuple[TrainStatus]:
        if not self.yahoo_app_id:
            self.logger.error("Yahoo APP ID is not set.")
            return ()

        for i in range(retry_times):
            try:
                params = {
                    "area": self.region.id,
                    "detail": "full",
                    "diainfo": "true",
                    "sortColumn": "publishTime",
                }

                headers = {
                    "User-Agent": f"; Yahoo AppID:{self.yahoo_app_id}",
                    "Accept-Language": "ja-JP",
                }

                r = self.session.get(
                    self.YAHOO_ENDPOINT,
                    params=params,
                    headers=headers,
                )

                r.raise_for_status()
                r = r.json()
                features = r.get("feature", [])

                train_statuses = []
                for feature in features:
                    routeinfo = feature.get("routeInfo", {})
                    property_data = routeinfo.get("property", {})
                    diainfo_list = property_data.get("diainfo", [])

                    for diainfo in diainfo_list:
                        train_statuses.append(
                            TrainStatus(
                                train=property_data.get("displayName", ""),
                                status=status_normalizer(diainfo.get("status", "")),
                                detail=diainfo.get("message", ""),
                            )
                        )

                return tuple(train_statuses)
            except JSONDecodeError as e:
                self.logger.error(f"JSON decode error from Yahoo. no retry: {e}")
                break
            except requests.Timeout as e:
                self.logger.warning(f"Request to Yahoo timed out: {e}")
            except requests.RequestException as e:
                if hasattr(e, "response") and e.response is not None:
                    status = e.response.status_code

                    if status == 403:
                        self.logger.error(
                            "Access forbidden. no retry. This may be due to an invalid APPID or because the access is originating from the EEA or the UK."
                        )
                        break
                    elif status == 429:
                        retry_after = e.response.headers.get("Retry-After")
                        if retry_after and retry_after.isdigit():
                            delay = float(retry_after)
                        else:
                            delay = 2**i
                        self.logger.warning(f"Rate limited. Retrying after {delay}s...")
                        time.sleep(delay)
                        continue
                    elif status >= 500:
                        self.logger.warning(
                            f"Server error ({status}). retrying... ({i + 1}/{retry_times}): {e}"
                        )
                    else:
                        self.logger.error(
                            f"Client error occurred while requesting Yahoo: {e}"
                        )
                        break
            except Exception as e:
                self.logger.error(f"Error requesting from Yahoo: {e}")

            if i < retry_times - 1:
                self.logger.info(f"Retrying... ({i + 1}/{retry_times})")
                time.sleep(self.retry_sleep)
                continue

        return ()
