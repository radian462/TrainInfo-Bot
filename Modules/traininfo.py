import json
import os
import re
from typing import Final, Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from redis import Redis

from Modules.make_logger import make_logger

load_dotenv()

STATUS_EMOJI: Final[dict] = {
    "運転見合わせ": "🛑",
    "列車遅延": "🕒",
    "運転情報": "ℹ️",
    "運転状況": "ℹ️",
    "運転計画": "🗒️",
    "交通障害情報": "🚧",
    "運転再開": "🚋",
    "平常運転": "🚋",
    "その他": "⚠️",
}

REGION_DATA: Final[dict] = {
    "関東": {
        "id": "4",
        "roman": "kanto",
        "db": os.getenv("KANTO_DB"),
    },
    "関西": {
        "id": "6",
        "roman": "kansai",
        "db": os.getenv("KANSAI_DB"),
    },
}

r = Redis(
    host=os.getenv("UPSTASH_HOST"),
    port=os.getenv("UPSTASH_PORT"),
    password=os.getenv("UPSTASH_PASS"),
    ssl=True,
    decode_responses=True,
)


class TrainInfo:
    def __init__(self, region: str):
        self.logger = make_logger(f"traininfo[{region}]")

        self.region: Final[str] = region
        self.region_id: Final[str] = REGION_DATA[region]["id"]
        self.region_roman: Final[str] = REGION_DATA[region]["roman"]
        self.region_db: Final[str] = REGION_DATA[region]["db"]

    def request_main_source(self) -> Optional[list[dict]]:
        try:
            url = f"https://www.nhk.or.jp/n-data/traffic/train/traininfo_area_0{self.region_id}.json"
            response = requests.get(url)

            original_data = (
                response.json()["channel"]["item"]
                + response.json()["channel"]["itemLong"]
            )

            data = [
                {
                    "train": o["trainLine"],
                    "status": o["status"],
                    "detail": o["textLong"],
                }
                for o in original_data
            ]

            self.logger.info("Get data from main source")

            return data
        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return None

    def request_sub_source(self) -> Optional[list[dict]]:
        try:
            url = "https://mainichi.jp/traffic/etc/a.html"
            response = requests.get(url)
            match = re.search(
                f'{self.region}エリア(.*?)<td colspan="3">',
                re.sub("<strong>", "\n", response.text),
                re.DOTALL,
            )
            if match is not None:
                region_html = match.group(1)
                soup = BeautifulSoup(region_html, "html.parser")

                region_text = re.sub("\n\n", "", soup.get_text())
                data_list = [
                    t for t in region_text.split() if re.search(r"[ぁ-ゖァ-ヶ一-龍]", t)
                ]

                train = [data_list[i] for i in range(0, len(data_list), 3)]
                status = [data_list[i + 1] for i in range(0, len(data_list) - 1, 3)]
                detail = [data_list[i + 2] for i in range(0, len(data_list) - 2, 3)]
                data = [
                    {"train": t, "status": s, "detail": d}
                    for t, s, d in zip(train, status, detail)
                ]

                self.logger.info("Get data from sub source")

                return data
            else:
                return []

        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return None

    def format_data(self, data) -> list[dict]:
        try:
            for d in data:
                for key in STATUS_EMOJI.keys():
                    if key in d["status"]:
                        d["status"] = STATUS_EMOJI[key] + key
                        break
                else:
                    d["status"] = "⚠️その他"
            return data
        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return []

    def request(self) -> list[dict]:
        try:
            data = self.request_main_source()
            if data is None:
                self.logger.warning("Request from main source failed")
                data = self.request_sub_source()

            return self.format_data(data)
        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return []

    def get_last_data(self) -> list[dict]:
        try:
            load_data = r.get(self.region_db)
            last_data = json.loads(load_data)
            self.logger.info(f"Load old data from {self.region_db}")
            if last_data is None:
                return []

            return last_data
        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return []

    def set_last_data(self, data: list[dict]):
        try:
            r.set(self.region_db, json.dumps(data))
            self.logger.info(f"Set data to {self.region_db}")
        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return []

    def merge_data(self, data, old) -> list[dict]:
        try:
            trains = set([d["train"] for d in data] + [d["train"] for d in old])
            merged = [
                {
                    "train": t,
                    "oldstatus": (
                        next(
                            (o["status"] for o in old if o["train"] == t), "🚋平常運転"
                        )
                    ),
                    "newstatus": (
                        next(
                            (d["status"] for d in data if d["train"] == t), "🚋平常運転"
                        )
                    ),
                    "detail": (
                        next(
                            (d["detail"] for d in data if d["train"] == t),
                            "現在、ほぼ平常通り運転しています。",
                        )
                    ),
                }
                for t in trains
            ]

            # 並び替え
            sort_list = [value + key for key, value in STATUS_EMOJI.items()]
            merged = [m for s in sort_list for m in merged if m["newstatus"] == s]

            # 変更点があるものを前に&平常運転→平常運転を削除
            merged = [m for m in merged if m["oldstatus"] != m["newstatus"]] + [
                m
                for m in merged
                if m["oldstatus"] == m["newstatus"] and m["newstatus"] != "🚋平常運転"
            ]

            return merged
        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return []

    def conv_message(self, data: list[dict]) -> list[str]:
        try:
            formatted_messages = []

            if not [d for d in data if d["oldstatus"] != d["newstatus"]]:
                self.logger.info("Data is the same")
                return ["運行状況に変更はありません。"]

            for d in data:
                if d["newstatus"] == d["oldstatus"]:
                    formatted_messages.append(
                        f"{d['train']} : {d['newstatus']}\n{d['detail']}"
                    )
                else:
                    formatted_messages.append(
                        f"{d['train']} : {d['oldstatus']}➡️{d['newstatus']}\n{d['detail']}"
                    )

            return formatted_messages
        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return []

    def process_message(self, messages: list[str], width: int = 300) -> list[str]:
        try:
            messages_list = []
            processing_message = ""

            if not messages:
                processing_message = self.region + "の電車は全て正常に運行しています。"
            elif messages == ["運行状況に変更はありません。"]:
                messages_list = messages
            else:
                for m in messages:
                    if len(processing_message + m + "\n\n") < width:
                        processing_message += m + "\n\n"
                    else:
                        messages_list.append(processing_message.rstrip("\r\n"))
                        processing_message = m + "\n\n"
                messages_list.append(processing_message.rstrip("\r\n"))

            return messages_list

        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            self.logger.debug(messages_list)
            return []

    def make_message(self, data: list[dict], width: int = 300) -> list[str]:
        try:
            last_data = self.get_last_data()
            merged = self.merge_data(data, last_data)

            if last_data != data:
                self.set_last_data(data)

            messages = self.conv_message(merged)
            return self.process_message(messages, width)

        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return []
