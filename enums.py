from enum import Enum


class AuthType(Enum):
    USERNAME_PASSWORD = "username_password"
    TOKEN = "token"


class Region(Enum):
    KANTO = ("kanto", 4)
    KANSAI = ("kansai", 6)

    def __init__(self, name: str, region_id: int):
        self._name_str = name
        self._region_id = region_id

    @property
    def id(self):
        return self._region_id

    @property
    def label(self):
        return self._name_str


class Service(Enum):
    BLUESKY = ("Bluesky",)
    MISSKEYIO = ("MisskeyIO",)

    @property
    def label(self):
        return self.value[0]

    @property
    def client(self):
        if self is Service.BLUESKY:
            from clients.bluesky import BlueskyClient

            return BlueskyClient
        elif self is Service.MISSKEYIO:
            from clients.misskeyio import MisskeyIOClient

            return MisskeyIOClient
