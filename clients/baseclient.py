from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class PostResponse:
    success: bool = False
    ref: str | None = None  # これを直接渡せばリプライできるよう設計する
    raw: dict[str, Any] | None = None
    error: str | None = None


class BaseSocialClient(ABC):
    @abstractmethod
    def login(self, *args: Any, **kwargs: Any) -> bool:
        """
        ログイン処理を行う

        Returns
        -------
        bool
            ログイン成功時にTrueを返す
        """
        pass

    @abstractmethod
    def post(
        self, text: str, reply_to: str | None = None, _retry: bool = True
    ) -> PostResponse:
        """
        投稿を行う

        Parameters
        ----------
        text : str
            投稿内容
        reply_to : str | dict | None, optional
            返信先の投稿情報
        _retry : bool, optional
            再試行するかどうか
        **kwargs
            その他の投稿オプション

        Returns
        -------
        PostResponse
            投稿結果
        """
        pass
