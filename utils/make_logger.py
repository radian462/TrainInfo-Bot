import os
from logging import DEBUG, FileHandler, Formatter, getLogger

from rich.logging import RichHandler

PROJECT_ROOT = os.path.dirname(os.path.abspath(os.path.join(__file__, "..", "..")))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
LOG_FILE_PATH = os.path.join(LOG_DIR, "output.log")


def clear_log_file():
    if os.path.exists(LOG_FILE_PATH):
        os.remove(LOG_FILE_PATH)


def make_logger(name: str, context: str | None = None):
    if context:
        name = rf"{name}\[{context}]"

    logger = getLogger(name)
    logger.setLevel(DEBUG)

    if not logger.handlers:
        os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
        rich_handler = RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_path=False,
        )
        rich_formatter = Formatter("[magenta]%(name)s[/magenta] %(message)s")
        rich_handler.setFormatter(rich_formatter)
        logger.addHandler(rich_handler)

        file_handler = FileHandler(LOG_FILE_PATH, mode="a", encoding="utf-8")
        file_formatter = Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


if __name__ == "__main__":
    logger = make_logger("make_logger", context="test")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
