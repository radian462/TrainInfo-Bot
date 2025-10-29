import json
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from helpers.make_logger import make_logger

from .normalizer import status_normalizer

logger = make_logger("request")
session = requests.session()


@dataclass(frozen=True)
class TrainStatus:
    train: str
    status: str
    detail: str


def request_from_NHK(region_id: int | str) -> tuple[TrainStatus, ...] | None:
    try:
        url = f"https://www.nhk.or.jp/n-data/traffic/train/traininfo_area_0{region_id}.json"
        r = session.get(url, timeout=10)
        r.raise_for_status()

        original_data = r.json()["channel"]["item"] + r.json()["channel"]["itemLong"]
        return tuple(
            TrainStatus(
                train=o["trainLine"],
                status=status_normalizer(o["status"]),
                detail=o["textLong"],
            )
            for o in original_data
        )

    except Exception:
        logger.error("Failed to get data from NHK", exc_info=True)
        return None


def request_from_yahoo(region_id: int | str) -> tuple[TrainStatus, ...] | None:
    """
    notes
    -----
    このコードはEEA及びイギリスのサーバーでは利用できません。403が返ってきます。
    https://privacy.yahoo.co.jp/notice/globalaccess.html
    """
    try:
        url = "https://transit.yahoo.co.jp/diainfo/area/" + str(region_id)
        r = session.get(url, timeout=10)
        r.raise_for_status()

        soup = BeautifulSoup(r.content, "html.parser")
        next_data = soup.find("script", id="__NEXT_DATA__")

        if next_data:
            if next_data.string is None:
                return None

            data = json.loads(next_data.string)
            diainfo_features = (
                data.get("props", {})
                .get("pageProps", {})
                .get("diainfoTrainFeatures", [])
            )

            extracted = [
                item for r in diainfo_features if isinstance(r, list) for item in r
            ]
            incident_rails = [
                r.get("routeInfo", {}).get("property", {})
                for r in extracted
                if "diainfo" in r.get("routeInfo", {}).get("property", {})
            ]

            return tuple(
                TrainStatus(
                    train=r.get("displayName"),
                    detail=r.get("diainfo", [])[0].get("message"),
                    status=status_normalizer(r.get("diainfo", [])[0].get("status")),
                )
                for r in incident_rails
            )
        else:
            return None
    except requests.HTTPError as e:
        if e.response.status_code == 403:
            logger.error(
                "Access forbidden: Are you accessing from the EEA or the UK? Yahoo blocks requests from those regions.",
                exc_info=True,
            )
            return None
        else:
            logger.error("HTTP error occurred", exc_info=True)
            return None
    except Exception:
        logger.error("Failed to get data from Yahoo", exc_info=True)
        return None


if __name__ == "__main__":
    print(request_from_NHK(3))
    print(request_from_yahoo(3))
