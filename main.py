from atproto import Client
import requests
import redis

class train_info:
    def __init__(self):
        self.region = "関東"
        self.bluesky_name = ""
        self.bluesky_pass = ""
        self.redis_host = ""
        self.redis_port = ""
        self.redis_pass = ""
        self.r = redis.Redis(
            host = self.redis_host,
            port = self.redis_port,
            password= self.redis_pass,
            ssl=True,
            decode_responses=True
        )

        self.client = Client()
        self.client.login(self.bluesky_name, self.bluesky_pass)

    