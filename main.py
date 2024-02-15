from atproto import Client
import time
import datetime
import requests
import re
import redis
import os
import json

r = redis.Redis(
  host='apn1-probable-gator-33492.upstash.io',
  port=33492,
  password= os.getenv("upstash_passward"),
  ssl=True
)

client = Client()
client.login("train-kanto.f5.si", os.getenv("password"))

second = datetime.datetime.now().time().second
time.sleep(60 - second)

old_message = ""

def get_traindata():
  site_source = requests.get("https://mainichi.jp/traffic/etc/a.html").text
  site_source = re.sub("\n" , "#" , site_source)

  site_data = re.search(r'関東エリア(.*?)<td colspan="3">', site_source).group(1)
  site_data = re.sub("#" , "\n" , site_data)

  train = re.findall(r'<td height="40"><font size="-1">(.*?)<BR><strong>', site_data)
  status = re.findall(r'>(.*?)</font></strong></font></td>', site_data)
  info = re.findall(r'<td height="40"><font size="-1">(.*?)</font></td>', site_data)

  emojidict = {"列車遅延": "🕒列車遅延", "運転見合わせ": "🛑運転見合わせ", "運転情報": "ℹ️運転情報", "運転状況": "ℹ️運転状況", "運転再開":"🚋運転再開","平常運転":"🚋平常運転","その他":"⚠️その他"}

  status = [emojidict.get(s, emojidict["その他"]) for s in status]
  data = [{"train": t, "status": s, "info": i} for t, s, i in zip(train, status, info)]

  return data

def merge_data(olddata,newdata):
  olddata_trains = [d["train"] for d in olddata]
  newdata_trains = [d["train"] for d in newdata]

  showdata = []
  for i, train in enumerate(newdata_trains):
    info = newdata[i]["info"]
    if train in olddata_trains:
      j = olddata_trains.index(train)
      newstatus = newdata[i]["status"]
      oldstatus = olddata[j]["status"]
    else:
      newstatus = newdata[i]["status"]
      oldstatus = "🚋平常運転"

    data = {"train":train,"oldstatus":oldstatus,"newstatus":newstatus,"info":info}
    showdata.append(data)

  for train in set(olddata_trains) - set(newdata_trains): 
    i = olddata_trains.index(train)
    newstatus = "🚋平常運転"
    oldstatus = olddata[i]["status"]
    info = "現在、ほぼ平常通り運転しています。"

    data = {"train":train,"oldstatus":oldstatus,"newstatus":newstatus,"info":info}
    showdata.append(data)

  return showdata

def make_message():
  olddata = r.get('kanto_train')
  olddata = json.loads(olddata)
  newdata = get_traindata()

  json_newdata = json.dumps(newdata)
  r.set("kanto_train", json_newdata)

  data = merge_data(olddata,newdata)
  data_trains = [d["train"] for d in data]

  message = ""
  for train in data_trains:
      t = data_trains.index(train)
      if olddata == newdata:
          message = "運行状況に変更はありません。"
          uri = r.get('kanto_train_uri').decode('utf-8').strip('"') 
          post_data = client.get_posts([uri])
          try:
            post_text = re.search(r"text='(.*?)'", str(post_data)).group(1)
            if post_text == message:
              client.delete_post(uri)
          except:
            pass
      else:
        if data == []:
          message = "関東の電車は全て正常に動いています"
        if data[t]["oldstatus"] == data[t]["newstatus"]:
          if data[t]["oldstatus"] != "🚋平常運転":
             message += f'{data[t]["train"]} : {data[t]["newstatus"]}\n{data[t]["info"]}\n\n'
        elif data[t]["oldstatus"] != data[t]["newstatus"]:
          message += f'{data[t]["train"]} : {data[t]["oldstatus"]}➡️{data[t]["newstatus"]}\n{data[t]["info"]}\n\n'

  while message.endswith('\n'):
    message= message[:-1]

  return message

while True:
    current_time = time.localtime()
    minutes = current_time.tm_min
    print(minutes)

    if minutes in [0,10,20,30,40,50,60]:
      message = make_message()
      print(message)
      post = client.send_post(text=message)
      r.set("kanto_train_uri", post.uri)
  
    time.sleep(60)
