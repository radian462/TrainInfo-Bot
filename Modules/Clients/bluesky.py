from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

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

    def _refresh_token(self):
        url = HOST + "com.atproto.server.refreshSession"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.refreshjwt}"
        }

        response = requests.post(url, headers=headers)
        session_data = response.json()

        self.accessjwt = session_data.get("accessJwt")
        self.refreshjwt = session_data.get("refreshJwt")

    def _parse_uri(self, uri: str) -> dict:
        try:
            parsed_uri = urlparse(uri)
            return {
                "repo": parsed_uri.netloc,
                "collection": parsed_uri.path.split("/")[1],
                "rkey": parsed_uri.path.split("/")[2]
            }
        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return {}


    def _get_reply_refs(self, uri: str) -> dict:
        try:
            url = HOST + "com.atproto.repo.getRecord"
            uri_parts = self._parse_uri(uri)

            r = requests.get(url, params=uri_parts)
            parent = r.json()

            parent_reply = parent["value"].get("reply")
            if parent_reply is not None:
                root_uri = parent_reply["root"]["uri"]
                root_repo, root_collection, root_rkey = root_uri.split("/")[2:5]
                r = requests.get(
                    HOST + "com.atproto.repo.getRecord",
                    params={
                        "repo": root_repo,
                        "collection": root_collection,
                        "rkey": root_rkey,
                    },
                )
                root = r.json()
            else:
                root = parent

            return {
                "root": {
                    "uri": root["uri"],
                    "cid": root["cid"],
                },
                "parent": {
                    "uri": parent["uri"],
                    "cid": parent["cid"],
                },
            }
        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return {}


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
                data["record"]["reply"] = self._get_reply_refs(reply_to["uri"])

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
