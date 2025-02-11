from datetime import datetime
from typing import Optional

import requests

from Modules.make_logger import make_logger

HOST = "https://bsky.social/xrpc/"


class Bluesky:
    def __init__(self):
        self.logger = make_logger("Bluesky")

    def login(self, identifier: str, password: str) -> dict:
        try:
            url = HOST + "com.atproto.server.createSession"

            data = {"identifier": identifier, "password": password}

            headers = {"Content-Type": "application/json"}

            response = requests.post(url, json=data, headers=headers)
            session_data = response.json()

            self.handle = session_data.get("handle")
            self.did = session_data.get("did")
            self.accessjwt = session_data.get("accessJwt")
            self.refreshjwt = session_data.get("refreshJwt")

            return session_data
        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return {}

    def _refresh_token(self) -> None:
        try:
            url = HOST + "com.atproto.server.refreshSession"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.refreshjwt}",
            }

            response = requests.post(url, headers=headers)
            session_data = response.json()

            self.accessjwt = session_data.get("accessJwt")
            self.refreshjwt = session_data.get("refreshJwt")
        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return None

    def post(self, text: str, reply_to: Optional[dict] = None) -> dict:
        try:
            """
            reply_toはこの関数の返り値かこのような辞書を渡す必要がある。
            {
                "uri": "example",
                "cid": "example"
            }
            """
            if not self.accessjwt:
                self.logger.error("Not logged in")
                return {}

            self._refresh_token()

            url = HOST + "com.atproto.repo.createRecord"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.accessjwt}",
            }
            data = {
                "repo": self.handle,
                "collection": "app.bsky.feed.post",
                "record": {
                    "$type": "app.bsky.feed.post",
                    "text": text,
                    "createdAt": datetime.utcnow().isoformat() + "Z",
                },
            }

            if reply_to:
                data["record"]["reply"] = {
                    "root": {
                        "uri": reply_to.get("uri"),
                        "cid": reply_to.get("cid"),
                    },
                    "parent": {
                        "uri": reply_to.get("uri"),
                        "cid": reply_to.get("cid"),
                    },
                }

            response = requests.post(url, json=data, headers=headers)

            return response.json()
        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return {}


if __name__ == "__main__":
    bluesky = Bluesky()
    bluesky.login("radian-test.bsky.social", "2w/kgju23")
    post = bluesky.post("Test")
    bluesky.post("Test2", post)
