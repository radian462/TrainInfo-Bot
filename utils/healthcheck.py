from threading import Thread

from bottle import route, run


@route("/")
def home():
    return "Bot is online."


def run_server():
    run(host="0.0.0.0", port=8080)


def healthcheck():
    t = Thread(target=run_server)
    t.start()
