from atproto import Client
import json
import os
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
        original_data = response.json()['channel']['item']

        data = [
            {
                'train': o['trainLine'],
                'status': o['status'],
                'detail': o['textLong'],
            }
            for o in original_data
        ]

        print(data)
        

kanto = TrainInfo(
    "関東",
    os.getenv("KANTO_NAME"),
    os.getenv("KANTO_PASS"),
    r
)

kanto.request()