from flask import Flask
import logging
from threading import Thread

l = logging.getLogger()
l.addHandler(logging.FileHandler("/dev/null"))
app = Flask("")


@app.route("/")
def home():
    return "Bot is online."


def run():
    app.run(host="0.0.0.0", port=8080)


def healthcheck():
    t = Thread(target=run)
    t.start()
