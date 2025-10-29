from misskey import Misskey
from misskey.exceptions import MisskeyAPIException

from ..make_logger import make_logger
from .baseclient import BaseSocialClient, PostResponse


class MisskeyIOClient(BaseSocialClient):
    def __init__(self):
        self.logger = make_logger("MisskeyIO")
        self.host: str = "https://misskey.io"
        self.token: str | None = None
        self.misskey: Misskey | None = None

    def login(self, token: str | None) -> bool:
        if not token:
            self.logger.error("Missing token")
            return False

        try:
            self.misskey = Misskey(self.host, i=token)
            meta = self.misskey.meta()

            if meta:
                self.logger.info("Login successful")
                return True
        except MisskeyAPIException as e:
            self.logger.error(f"Misskey API Error: {e.message}", exc_info=True)
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
        Misskey.ioに投稿

        Parameters
        ----------
        text : str
            投稿内容
        reply_to : str | None, optional
            返信先の投稿情報
        _retry : bool, optional
            再試行するかどうか

        Returns
        -------
        PostResponse
            投稿結果

        notes
        -----
        401エラーが発生した場合、再試行は行わない
        returnした投稿情報を直接渡せばリプライが可能
        """
        if not self.misskey:
            self.logger.error("Client not logged in")
            return PostResponse(success=False, error="Client not logged in")

        try:
            result = self.misskey.notes_create(text=text, reply_id=reply_to)
            return PostResponse(
                success=True,
                ref=result.get("createdNote", {}).get("id"),
                raw=result,
            )
        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return PostResponse(success=False, error="An exception occurred")
