from logging import DEBUG, Formatter, getLogger

from rich.logging import RichHandler


def make_logger(name: str, context: str | None = None):
    logger = getLogger(name)
    logger.setLevel(DEBUG)
    if not logger.handlers:
        handler = RichHandler(rich_tracebacks=True, markup=True)
        if context:
            formatter = Formatter(f"[magenta]%(name)s[/magenta][{context}] %(message)s")
        else:
            formatter = Formatter("[magenta]%(name)s[/magenta] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

