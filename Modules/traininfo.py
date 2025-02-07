import json
import os
import re
from typing import final

import requests
from bs4 import BeautifulSoup
from redis import Redis

from Modules.make_logger import make_logger

STATUS_EMOJI: final = {
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

REGION_DATA: final = {
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


class TrainInfo:
    def __init__(self, region: str):
        self.logger = make_logger(f"traininfo[{region}]")
        self.r = Redis(
            host=os.getenv("UPSTASH_HOST"),
            port=os.getenv("UPSTASH_PORT"),
            password=os.getenv("UPSTASH_PASS"),
            ssl=True,
            decode_responses=True,
        )

        self.region = region

    def request(self) -> dict:
        url = f"https://www.nhk.or.jp/n-data/traffic/train/traininfo_area_0{REGION_DATA[self.region]["id"]}.json"
        response = requests.get(url)

        if response.status_code == 200:
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
        else:
            url = "https://mainichi.jp/traffic/etc/a.html"
            response = requests.get(url)
            region_html = re.search(
                f'{self.region}エリア(.*?)<td colspan="3">',
                re.sub("<strong>", "\n", response.text),
                re.DOTALL,
            ).group(1)
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

        for d in data:
            for key in STATUS_EMOJI.keys():
                if key in d["status"]:
                    d["status"] = STATUS_EMOJI[key] + key
                    break
                else:
                    d["status"] = "⚠️その他"

        return data

    def make_message(self, data) -> list[str]:
        old = json.loads(self.r.get(REGION_DATA[self.region]["db"]))
        self.logger.info("Load old data")
        trains = set([d["train"] for d in data] + [d["train"] for d in old])
        merged = [
            {
                "train": t,
                "oldstatus": (
                    next((o["status"] for o in old if o["train"] == t), "🚋平常運転")
                ),
                "newstatus": (
                    next((d["status"] for d in data if d["train"] == t), "🚋平常運転")
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
        if not [m for m in merged if m["oldstatus"] != m["newstatus"]]:
            self.logger.info("Data is the same")
            return ["運行状況に変更はありません。"]

        # 並び替え
        sort_list = [value + key for key, value in STATUS_EMOJI.items()]
        merged = [m for s in sort_list for m in merged if m["newstatus"] == s]

        # 変更点があるものを前に&平常運転→平常運転を削除
        merged = [m for m in merged if m["oldstatus"] != m["newstatus"]] + [
            m
            for m in merged
            if m["oldstatus"] == m["newstatus"] and m["newstatus"] != "🚋平常運転"
        ]
        messages = []

        for m in merged:
            if m["newstatus"] == m["oldstatus"]:
                messages.append(f"{m['train']} : {m['newstatus']}\n{m['detail']}")
            else:
                messages.append(
                    f"{m['train']} : {m['oldstatus']}➡️{m['newstatus']}\n{m['detail']}"
                )

        self.r.set(REGION_DATA[self.region]["db"], json.dumps(data))
        self.logger.info("Upload data")

        messages_list = []
        processing_message = ""
        if not messages:
            processing_message = self.region + "の電車は全て正常に運行しています。"
        elif messages == ["運行状況に変更はありません。"]:
            messages_list = messages
        else:
            for m in messages:
                if len(processing_message + m + "\n\n") < 300:
                    processing_message += m + "\n\n"
                else:
                    messages_list.append(processing_message.rstrip("\r\n"))
                    processing_message = m + "\n\n"
            messages_list.append(processing_message.rstrip("\r\n"))

        return messages_list
