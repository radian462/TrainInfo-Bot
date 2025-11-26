import os
from threading import Thread

from bottle import Bottle, request, response, static_file

from ..make_logger import LOG_FILE_PATH

app = Bottle()


@app.route("/")
def root():
    return "I'm alive!"


@app.route("/logs")
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


def server_run():
    def _run():
        app.run(host="0.0.0.0", port=8080)

    t = Thread(target=_run, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    import dotenv

    dotenv.load_dotenv()
    server_run()
    input("Server is running. Press Enter to exit...\n")
