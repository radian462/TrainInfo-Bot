import requests

from enums import Region

from ..normalizer import status_normalizer
from ..trainstatus import TrainStatus
from .baseclient import BaseTrainInfoClient


class YahooClient(BaseTrainInfoClient):
    def __init__(
        self,
        session: requests.Session,
        region: Region,
        timeout: int = 10,
        retry_sleep: float = 1.0,
        retry_times: int = 3,
        yahoo_app_id: str | None = None,
    ):
        super().__init__(
            session=session,
            region=region,
            timeout=timeout,
            retry_sleep=retry_sleep,
            retry_times=retry_times,
        )
        self.yahoo_app_id = yahoo_app_id
        self.YAHOO_ENDPOINT = (
            "https://cache-diainfo-transit.yahooapis.jp/v4/diainfo/train"
        )

    def _fetch(self) -> tuple[TrainStatus, ...]:
        if not self.yahoo_app_id:
            self.logger.error("Missing Yahoo App ID")
            return ()

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

    def _status_exception_handler(
        self, status: int, e: Exception, i: int
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
            case 403:
                self.logger.error(
                    "Access forbidden. no retry. This may be due to an invalid APPID or because the access is originating from the EEA or the UK."
                )
                return (False, None)
            case _ if status >= 500:
                self.logger.warning(
                    f"Server error ({status}). retrying... ({i + 1}/{self.retry_times}): {e}"
                )
                return (True, None)
            case _:
                self.logger.error(f"Client error occurred while requesting: {e}")
                return (False, None)
