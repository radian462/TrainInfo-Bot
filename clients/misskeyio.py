from misskey import Misskey
from misskey.exceptions import MisskeyAPIException

from enums import AuthType, Service
from helpers.make_logger import make_logger

from .baseclient import BaseSocialClient, PostResponse


class MisskeyIOClient(BaseSocialClient):
    def __init__(self, context: str | None = None) -> None:
        self.logger = make_logger(type(self).__name__, context=context)
        super().__init__(
            service_name=Service.MISSKEYIO,
            auth_type=AuthType.TOKEN,
            post_string_limit=3000,
        )

        self.token: str | None = None
        self.misskey: Misskey | None = None

        self.HOST: str = "https://misskey.io"

    def login(self, token: str | None) -> bool:
        if not token:
            self.logger.error("Missing token")
            return False

        try:
            self.misskey = Misskey(self.HOST, i=token)
            meta = self.misskey.meta()

            if meta:
                self.logger.info("Login successful")
            return bool(meta)
        except MisskeyAPIException as e:
            self.logger.error(f"Misskey API Error: {e.message}", exc_info=True)
            return False
        except Exception:
            self.logger.error("An error occurred", exc_info=True)
            return False

    def post(
        self,
        text: str,
        reply_to: str | None = None,
        max_retries: int = 3,
    ) -> PostResponse:
        """
        Misskey.ioに投稿

        Parameters
        ----------
        text : str
            投稿内容
        reply_to : str | None, optional
            返信先の投稿情報
        max_retries : int
            最大再試行回数

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

        for i in range(max_retries):
            try:
                result = self.misskey.notes_create(text=text, reply_id=reply_to)
                return PostResponse(
                    success=True,
                    ref=result.get("createdNote", {}).get("id"),
                    raw=result,
                )
            except Exception:
                self.logger.error("An error occurred", exc_info=True)
                if i < max_retries - 1:
                    self.logger.info(f"Retrying... ({i + 1}/{max_retries})")
                    continue

        return PostResponse(success=False, error="An exception occurred")
