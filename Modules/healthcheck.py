import logging
from threading import Thread

from bottle import route, run

l = logging.getLogger()
l.addHandler(logging.FileHandler("/dev/null"))


@route("/")
def home():
    return "Bot is online."


def run_server():
    run(host="0.0.0.0", port=8080)


def keep_alive():
    t = Thread(target=run_server)
    t.start()