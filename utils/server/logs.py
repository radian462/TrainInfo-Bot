import base64
import os

from bottle import Bottle, request, response, static_file

from ..make_logger import LOG_FILE_PATH

logs_app = Bottle()

LOGS_USER = "admin"


def auth(header: str) -> bool:
    LOGS_PASSWORD = os.getenv("LOG_PASSWORD") or None

    # パスワード未設定時は認証不要
    if not LOGS_PASSWORD:
        return True

    try:
        auth_type, encoded_credentials = header.split(" ", 1)
        if auth_type.lower() != "basic":
            return False

        decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
        username, password = decoded_credentials.split(":", 1)
        return username == LOGS_USER and password == LOGS_PASSWORD
    except Exception:
        return False


@logs_app.route("/", method=["GET"])
def get_logs():
    if not auth(request.headers.get("Authorization", "")):
        response.status = 401
        response.headers["WWW-Authenticate"] = (
            'Basic realm="Logs Access", charset="UTF-8"'
        )
        return "Authentication required."

    try:
        return static_file(LOG_FILE_PATH, root="/", download=True)
    except FileNotFoundError:
        response.status = 404
        return "Log file not found."
    except Exception as e:
        response.status = 500
        return f"Error: {e}"
