from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests

from enums import AuthType, Service
from helpers.make_logger import make_logger

from .baseclient import BaseSocialClient, PostResponse


class BlueskyClient(BaseSocialClient):
    def __init__(self):
        super().__init__(
            service_name=Service.BLUESKY,
            auth_type=AuthType.USERNAME_PASSWORD,
            post_string_limit=300,
        )
        self.logger = make_logger(Service.BLUESKY.label)
        self.session = requests.Session()
        self.session.headers.update({"Connection": "keep-alive"})

        self.handle: str | None = None
        self.did: str | None = None
        self.accessjwt: str | None = None
        self.refreshjwt: str | None = None

        self.last_refresh: datetime | None = None
        self.refresh_interval: int = 3600  # seconds

        self.HOST = "https://bsky.social/xrpc/"
        self.LOGIN_ENDPOINT = "com.atproto.server.createSession"
        self.REFRESH_SESSION_ENDPOINT = "com.atproto.server.refreshSession"
        self.GET_RECORD_ENDPOINT = "com.atproto.repo.getRecord"
        self.CREATE_RECORD_ENDPOINT = "com.atproto.repo.createRecord"

    def login(self, identifier: str | None, password: str | None) -> bool:
        if not identifier or not password:
            self.logger.error("Missing credentials")
            return False

        try:
            url = self.HOST + self.LOGIN_ENDPOINT

            response = self.session.post(
                url,
                json={"identifier": identifier, "password": password},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            session_data = response.json()

            self.handle = session_data.get("handle")
            self.did = session_data.get("did")
            self.accessjwt = session_data.get("accessJwt")
            self.refreshjwt = session_data.get("refreshJwt")

            if all([self.handle, self.did, self.accessjwt, self.refreshjwt]):
                self.last_refresh = datetime.now(timezone.utc)
                self.logger.info("Login successful")
                return True
        except Exception:
            self.logger.error("An error occurred", exc_info=True)
        return False

    def post(
        self,
        text: str,
        reply_to: str | None = None,
        _retry: bool = True,
    ) -> PostResponse:
        """
        Blueskyに投稿

        Parameters
        ----------
        text : str
            投稿内容
        reply_to : str | None, optional
            返信先の投稿情報
        _retry : bool, optional
            トークン更新後に再試行するかどうか

        Returns
        -------
        PostResponse
            投稿結果

        notes
        -----
        401エラーが発生した場合、トークンを更新して再試行する。ただし、再試行は一度だけ行う
        returnした投稿情報を直接渡せばリプライが可能
        """
        try:
            if not self.accessjwt:
                self.logger.error("Not logged in")
                return PostResponse(success=False, error="Not logged in")

            self._refresh_token()

            url = self.HOST + self.CREATE_RECORD_ENDPOINT
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.accessjwt}",
            }
            data: dict[str, Any] = {
                "repo": self.handle,
                "collection": "app.bsky.feed.post",
                "record": {
                    "$type": "app.bsky.feed.post",
                    "text": text,
                    "createdAt": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%S.%fZ"
                    ),
                },
            }

            if reply_to:
                data["record"]["reply"] = self._get_reply_refs(reply_to)

            response = self.session.post(url, json=data, headers=headers, timeout=10)
            response.raise_for_status()

            return PostResponse(
                success=True, ref=response.json().get("uri"), raw=response.json()
            )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401 and _retry:
                self.logger.warning(
                    "Failed to authenticate.token may be expired.\n Refreshing token and retrying..."
                )
                self._request_refresh_jwt()
                return self.post(text, reply_to, _retry=False)
            else:
                raise
        except Exception as e:
            self.logger.error("An error occurred", exc_info=True)
            return PostResponse(success=False, error=str(e))

    def _request_refresh_jwt(self) -> None:
        try:
            url = self.HOST + self.REFRESH_SESSION_ENDPOINT
            response = self.session.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.refreshjwt}",
                },
                timeout=10,
            )
            response.raise_for_status()
            session_data = response.json()

            if session_data.get("accessJwt") and session_data.get("refreshJwt"):
                self.accessjwt = session_data.get("accessJwt")
                self.refreshjwt = session_data.get("refreshJwt")
                self.last_refresh = datetime.now(timezone.utc)
                self.logger.info("Refreshed JWT")
            else:
                self.logger.error("Failed to refresh JWT")
                return

        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return

    def _should_refresh(self) -> bool:
        if self.last_refresh is None:
            return True
        elapsed_time = (datetime.now(timezone.utc) - self.last_refresh).total_seconds()
        return elapsed_time > self.refresh_interval

    def _refresh_token(self) -> None:
        if self._should_refresh():
            self._request_refresh_jwt()

    def _parse_uri(self, uri: str) -> dict:
        try:
            parsed_uri = urlparse(uri)
            parts = parsed_uri.path.split("/")
            if len(parts) < 3:
                self.logger.error("Invalid URI format")
                return {}

            return {
                "repo": parsed_uri.netloc,
                "collection": parts[1],
                "rkey": parts[2],
            }
        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return {}

    def _get_reply_refs(self, uri: str) -> dict[str, dict]:
        try:
            url = self.HOST + self.GET_RECORD_ENDPOINT
            uri_parts = self._parse_uri(uri)

            r = self.session.get(url, params=uri_parts, timeout=10)
            r.raise_for_status()
            parent = r.json()

            parent_reply = parent.get("value", {}).get("reply")
            if parent_reply is not None:
                root_uri = parent_reply.get("root", {}).get("uri")
                root_repo, root_collection, root_rkey = root_uri.split("/")[2:5]
                r = self.session.get(
                    url,
                    params={
                        "repo": root_repo,
                        "collection": root_collection,
                        "rkey": root_rkey,
                    },
                    timeout=10,
                )
                r.raise_for_status()
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


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()
    client = BlueskyClient()
    if client.login(os.getenv("BLUESKY_KANTO_NAME"), os.getenv("BLUESKY_KANTO_PASS")):
        response = client.post("Hello, Bluesky!")
        if response.success:
            print(f"Posted successfully! URI: {response.ref}")
            client.post("This is a reply!", reply_to=response.ref)
        else:
            print(f"Failed to post: {response.error}")
