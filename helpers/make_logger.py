from logging import DEBUG, Formatter, getLogger

from rich.logging import RichHandler


def make_logger(name: str, context: str | None = None):
    if context:
        name = rf"{name}\[{context}]"

    logger = getLogger(name)
    logger.setLevel(DEBUG)
    if not logger.handlers:
        handler = RichHandler(rich_tracebacks=True, markup=True)
        formatter = Formatter("[magenta]%(name)s[/magenta] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


if __name__ == "__main__":
    logger = make_logger("make_logger", context="test")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
