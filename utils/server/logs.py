import os

from bottle import Bottle, request, response, static_file

from ..make_logger import LOG_FILE_PATH

logs_app = Bottle()


@logs_app.route("/")
def get_logs():
    LOGS_PASSWORD = os.getenv("LOG_PASSWORD")
    print(LOGS_PASSWORD)
    if LOGS_PASSWORD:
        submitted = request.query.password
        if submitted != LOGS_PASSWORD:
            return """
            <script>
                let password = prompt("Enter logs password:");
                if(password != null){
                    window.location.href = "/logs?password=" + encodeURIComponent(password);
                }
            </script>
            """

    try:
        return static_file(LOG_FILE_PATH, root="/", download=True)
    except FileNotFoundError:
        response.status = 404
