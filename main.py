from atproto import Client
import requests
import re
import time
import datetime
import os

client = Client()
client.login("train-bot.f5.si", os.getenv("passward"))


train_data = requests.get("https://ntool.online/data/train_all.json").json()
kanto = train_data['data']['4']

second = datetime.datetime.now().time().second
time.sleep(60 - second)

while True:
    railName = []
    status = []
    railCode = []
    info = []
    current_time = time.localtime()
    minutes = current_time.tm_min
    print(minutes)

    if minutes in [0, 15, 30, 45]:
        for i in kanto:
            if i["status"] != "平常運転":
                railName.append(i["railName"])
                status.append(i["status"])
                railCode.append(i["railCode"])

        for i in railCode:
            info_sourse = requests.get(f"https://transit.yahoo.co.jp/diainfo/{i}/0").text
            info_sourse = re.search(r'<dd class="trouble"><p>(.*?)<span>', info_sourse)
            if info_sourse is not None:
              info.append(info_sourse.group(1))
            else:
              info.append("詳細の取得に失敗しました")

        message = ""
        if railName == []:
            message = "関東の電車は全て正常に動いています"
        else:
          for i in range(len(railName)):
              message += f"{railName[i]}:{status[i]}\n{info[i]}\n\n"

        client.send_post(text=message)
    
    time.sleep(60)
