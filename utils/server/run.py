from threading import Thread

from bottle import Bottle

from .logs import logs_app

app = Bottle()
app.mount("/logs", logs_app)


@app.route("/")
def root():
    return "I'm alive!"


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
