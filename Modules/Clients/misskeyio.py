import misskey


class MisskeyIO:
    def __init__(self, token: str):
        self.client = misskey.Misskey(address="https://misskey.io", i=token)

    def note(self, text: str, reply_id: str | None = None) -> str:
        result = self.client.notes_create(text=text, reply_id=reply_id)
        return result.get("createdNote", {}).get("id")
