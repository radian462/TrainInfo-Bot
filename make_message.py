import requests
import re
import redis
import os
import json

r = redis.Redis(
  host= os.getenv("UPSTASH_HOST"),
  port= os.getenv("UPSTASH_PORT"),
  password= os.getenv("UPSTASH_PASS"),
  ssl=True,
  decode_responses=True
)

def get_traindata(region):  
    try:
        site_source = requests.get("https://mainichi.jp/traffic/etc/a.html").text
        site_source = re.sub("\n" , "#" , site_source)

        if region == "kanto":
            search_word = r'関東エリア(.*?)<td colspan="3">'
        elif region == "kansai":
            search_word = r'関西エリア(.*?)<td colspan="6">'
        site_data = re.search(search_word, site_source).group(1)
        site_data = re.sub("#" , "\n" , site_data)

        train = re.findall(r'<td height="40"><font size="-1">(.*?)<BR><strong>', site_data)
        status = re.findall(r'>(.*?)</font></strong></font></td>', site_data)
        info = re.findall(r'<td height="40"><font size="-1">(.*?)</font></td>', site_data)
    except:
        if region == "kanto":
            area = "04"
        elif region == "kansai":
            area = "06"
        response = requests.get(f"https://www.yomiuri.co.jp/traffic/area{area}/").text
        response = re.sub(" ","",response)
        response = re.sub("\n","#",response)

        site_data = re.search(r'<h1class="p-header-category-current-title">(.*?)<divclass="layout-contents__sidebar">', response).group(1)
        site_data = re.sub("#" , "\n" , site_data)

        train = re.findall(r'(.*?)<spanclass="traffic-area-wrap-mass__info--', site_data)
        status = re.findall(r'">(.*?)</span>\n</h4>', site_data)
        info = re.findall(r'<p>(.*?)</p>\n</article>',site_data)

    emojidict = {"列車遅延": "🕒列車遅延", "運転見合わせ": "🛑運転見合わせ", "運転情報": "ℹ️運転情報", "運転状況": "ℹ️運転状況", "運転再開":"🚋運転再開","平常運転":"🚋平常運転","運転計画":"🗒️運転計画","その他":"⚠️その他"}

    for i in range(len(status)):
        if "運転計画" in status[i]:
          status[i] = "運転計画"

    status = [emojidict.get(s, emojidict["その他"]) for s in status]
    data = [{"train": t, "status": s, "info": i} for t, s, i in zip(train, status, info)]
    return data

def data_upload(region,data):
    if region == "kanto":
        r.set("kanto_train",json.dumps(data))
    elif region == "kansai":
        r.set("kansai_train",json.dumps(data))


def merge_data(now, old):
    merged_data = []
    for d in now:
        old_entry = next((entry for entry in old if entry["train"] == d["train"]), None)
        if old_entry:
            if old_entry["status"] == d["status"] and d["status"] != "🚋平常運転":
                merged_dict = {
                    "train": d["train"],
                    "oldstatus": old_entry["status"],
                    "nowstatus": d["status"],
                    "info": d["info"]
                }
                merged_data.append(merged_dict)
            old.remove(old_entry)
        else:
            merged_dict = {
                "train": d["train"],
                "oldstatus": "🚋平常運転",
                "nowstatus": d["status"],
                "info": d["info"]
            }
            merged_data.append(merged_dict)

    for d in old:
        merged_dict = {
            "train": d["train"],
            "oldstatus": d["status"],
            "nowstatus": "🚋平常運転",
            "info": d["info"]
        }
        merged_data.append(merged_dict)
    return merged_data

def make_message(data):
    message = ""
    if data == []:
        message = "現在、電車は全て正常に動いています"
        return message

    if data == ["運行状況に変更はありません。"]:
        message = "運行状況に変更はありません。"
        return message

    for d in data:
        if d["oldstatus"] == d["nowstatus"]:
            if not d["oldstatus"] == "🚋運転再開":
                message += f'{d["train"]} : {d["nowstatus"]}\n{d["info"]}\n\n'
        else:
                message += f'{d["train"]} : {d["oldstatus"]} ➡️{d["nowstatus"]}\n{d["info"]}\n\n'

    return message

def load_data(region):
    if region == "kanto":
        olddata = r.get("kanto_train")
    elif region == "kansai":
        olddata = r.get("kansai_train")
    olddata = json.loads(olddata)
    return olddata

if __name__ == "__main__":
    get_traindata("kanto")
