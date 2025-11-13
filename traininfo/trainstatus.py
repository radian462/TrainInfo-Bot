from dataclasses import dataclass


@dataclass(frozen=True)
class TrainStatus:
    train: str
    status: str  # status_normalizerで正規化する
    detail: str
