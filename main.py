import atproto
from bs4 import BeautifulSoup
from datetime import datetime
import json
import logging
from logging import getLogger, INFO
import os
import re
import requests
from redis import Redis
from threading import Thread
import time

r = Redis(
    host=os.getenv("UPSTASH_HOST"),
    port=os.getenv("UPSTASH_PORT"),
    password=os.getenv("UPSTASH_PASS"),
    ssl=True,
    decode_responses=True,
)


class TrainInfo:
    def __init__(self, region, bluesky_name, bluesky_pass, r):
        self.region_data = {
            "関東": {
                "id": "4",
                "roman": "kanto",
                "db": "kanto_train_test",
            },
            "関西": {
                "id": "6",
                "roman": "kansai",
                "db": "kansai_train_test",
            },
        }

        self.region = region
        self.bluesky_name = bluesky_name
        self.bluesky_pass = bluesky_pass

        self.r = r

        self.logger = getLogger(self.region_data[self.region]["roman"])
        self.logger.setLevel(INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(levelname)s:%(name)s] %(message)s - %(asctime)s"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.client = atproto.Client()
        self.client.login(self.bluesky_name, self.bluesky_pass)

        self.logger.info("Bluesky Login")

    def request(self):
        url = f"https://www.nhk.or.jp/n-data/traffic/train/traininfo_area_0{self.region_data[self.region]["id"]}.json"
        response = requests.get(url)
       
        if response.status_code == 200:
            original_data = (
                response.json()["channel"]["item"]
                + response.json()["channel"]["itemLong"]
            )

            data = [
                {
                    "train": o["trainLine"],
                    "status": re.sub(r"^.*? ", "", o["title"]),
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

        status_emoji = {
            "平常運転": "🚋",
            "運転再開": "🚋",
            "運転計画": "🗒️",
            "運転情報": "ℹ️",
            "運転状況": "ℹ️",
            "列車遅延": "🕒",
            "運転見合わせ": "🛑",
            "その他": "⚠️",
        }

        for d in data:
            for key in status_emoji.keys():
                if key in d["status"]:
                    d["status"] = status_emoji[key] + key

        return data

    def make_message(self, data):
        old = json.loads(self.r.get(self.region_data[self.region]["db"]))
        self.logger.info("Load old data")

        if old == data:
            self.logger.info("Data is the same")
            return ["運行状況に変更はありません。"]

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

        # 変更点があるものを前に
        merged = [m for m in merged if m["oldstatus"] != m["newstatus"]] + [
            m for m in merged if m["oldstatus"] == m["newstatus"]
        ]

        messages = []
        for m in merged:
            if m["newstatus"] == m["oldstatus"]:
                messages.append(f"{m['train']} : {m['newstatus']}\n{m['detail']}")
            else:
                messages.append(
                    f"{m['train']} : {m['oldstatus']}➡️{m['newstatus']}\n{m['detail']}"
                )

        self.r.set(self.region_data[self.region]["db"], json.dumps(data))
        self.logger.info("Upload data")
        return messages

    def post(self, messages, service="Bluesky"):
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
                    messages_list.append(processing_message)
                    processing_message = m + "\n\n"
            messages_list.append(processing_message)

        if service == "Bluesky":
            latest_post = (
                self.client.get_author_feed(actor=self.bluesky_name, limit=1)
                .feed[0]
                .post.record.text
            )
            if latest_post == "運行状況に変更はありません。" and messages_list == [
                "運行状況に変更はありません。"
            ]:
                self.logger.info("Pending for the same post")
            else:
                for i, m in enumerate(messages_list):
                    if messages_list.index(m) == 0:
                        post = self.client.send_post(m)
                        root_post_ref = atproto.models.create_strong_ref(post)
                    elif messages_list.index(m) == 1:
                        reply_to_root = atproto.models.create_strong_ref(
                            self.client.send_post(
                                text=m,
                                reply_to=atproto.models.AppBskyFeedPost.ReplyRef(
                                    parent=root_post_ref, root=root_post_ref
                                ),
                            )
                        )
                    else:
                        reply_to_root = atproto.models.create_strong_ref(
                            self.client.send_post(
                                text=m,
                                reply_to=atproto.models.AppBskyFeedPost.ReplyRef(
                                    parent=reply_to_root, root=root_post_ref
                                ),
                            )
                        )
                    self.logger.info(f"Successfully post to Bluesky {i + 1}")

                self.logger.info("Done with posted to Bluesky")

    def main(self):
        interval = 10
        while True:
            minutes, seconds = datetime.now().minute, datetime.now().second
            
            if minutes % interval == 0:
                data = self.request()
                messages = self.make_message(data)
                self.post(messages)

            next_minute = (minutes // interval + 1) * interval
            wait_time = (next_minute - minutes) * 60 - seconds
            self.logger.info(f"Sleep {wait_time} seconds")
            time.sleep(wait_time)

kanto = TrainInfo("関東", os.getenv("KANTO_NAME"), os.getenv("KANTO_PASS"), r)
kansai = TrainInfo("関西", os.getenv("KANTO_NAME"), os.getenv("KANTO_PASS"), r)

thread1 = Thread(target=kanto.main)
thread2 = Thread(target=kansai.main)
thread1.start()
thread2.start()
thread1.join()
thread2.join()