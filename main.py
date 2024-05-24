import make_message as m
import post as p
import time
import datetime

interval = 10

while True:
    current_time = time.localtime()
    minutes = current_time.tm_min
  
    if minutes % interval == 0:
        for r in ["kanto","kansai"]:
            old = m.load_data(r)
            new = m.get_traindata(r)
            m.data_upload(r,new)
            merged = m.merge_data(new,old)
            message = m.make_message(merged)
            p.post_bluesky(r,message)

    wait_time = 60 - datetime.datetime.now().time().second
    print(f"{wait_time}秒待機します")
    time.sleep(wait_time)
      
