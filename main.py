from atproto import Client
from bs4 import BeautifulSoup
import json
import os
import re
import requests
from redis import Redis

r = Redis(
    host = os.getenv("UPSTASH_HOST"),
    port = os.getenv("UPSTASH_PORT"),
    password= os.getenv("UPSTASH_PASS"),
    ssl=True,
    decode_responses=True
)

class TrainInfo:
    def __init__(self, region, bluesky_name, bluesky_pass, r):
        self.region = region
        self.bluesky_name = bluesky_name
        self.bluesky_pass = bluesky_pass

        self.r = r
        
        '''
        self.client = Client()
        self.client.login(self.bluesky_name, self.bluesky_pass)

        print(region + "リージョンログイン")
        '''

    def request(self):
        regions = {"関東":"4","関西":"6"}
        url = f"https://www.nhk.or.jp/n-data/traffic/train/traininfo_area_0{regions[self.region]}.json"
        response = requests.get(url)
        if response.status_code == 200:
            original_data = response.json()['channel']['item'] + response.json()['channel']['itemLong']

            data = [
                {
                    'train': o['trainLine'],
                    'status': re.sub(r'^.*? ', '', o['title']),
                    'detail': o['textLong'],
                }
                for o in original_data
            ]
        else:
            url = "https://mainichi.jp/traffic/etc/a.html"
            response = requests.get(url)
            region_html = re.search(f'{self.region}エリア(.*?)<td colspan="3">', re.sub('<strong>', '\n', response.text), re.DOTALL).group(1)
            soup = BeautifulSoup(region_html, 'html.parser')
            region_text = re.sub('\n\n', '', soup.get_text())

            data_list = [t for t in region_text.split() if re.search(r'[ぁ-ゖァ-ヶ一-龍]', t)]
            train = [data_list[i] for i in range(0, len(data_list), 3)]
            status = [data_list[i+1] for i in range(0, len(data_list) - 1, 3)]
            detail = [data_list[i+2] for i in range(0, len(data_list) - 2, 3)]
            
            data = [{"train": t, "status": s, "detail": d} for t, s, d in zip(train, status, detail)]

        return data
                


kanto = TrainInfo(
    "関東",
    os.getenv("KANTO_NAME"),
    os.getenv("KANTO_PASS"),
    r
)

print(kanto.request())