import atproto

from Modules.make_logger import make_logger


class Bluesky:
    def __init__(self, bluesky_name: str, bluesky_pass: str, region: str):
        self.bluesky_name = bluesky_name
        self.bluesky_pass = bluesky_pass

        self.client = atproto.Client()
        self.client.login(self.bluesky_name, self.bluesky_pass)

        self.logger = make_logger(f"Bluesky[{region}]")
        self.logger.info(f"Login to {bluesky_name}")

    def post(self, messages_list: list[str]) -> None:
        try:
            if messages_list == ["運行状況に変更はありません。"]:
                self.logger.info("Pending for the same post")
            else:
                for i, m in enumerate(messages_list):
                    if messages_list.index(m) == 0:
                        post = self.client.send_post(m)
                        root_post_ref = atproto.models.create_strong_ref(post)
                    elif messages_list.index(m) == 1:
                        reply_to_root = atproto.models.create_strong_ref(
                            self.client.send_post(
                                text=m,
                                reply_to=atproto.models.AppBskyFeedPost.ReplyRef(
                                    parent=root_post_ref, root=root_post_ref
                                ),
                            )
                        )
                    else:
                        reply_to_root = atproto.models.create_strong_ref(
                            self.client.send_post(
                                text=m,
                                reply_to=atproto.models.AppBskyFeedPost.ReplyRef(
                                    parent=reply_to_root, root=root_post_ref
                                ),
                            )
                        )
                    self.logger.info(f"Successfully post {i + 1}")

                self.logger.info("Done with posted")
        except Exception:
            self.logger.error("An error occurred", exc_info=True)
