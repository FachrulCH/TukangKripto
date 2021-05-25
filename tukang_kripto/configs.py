import json


def read_config():
    f = open("config.json")
    return json.load(f)


config = read_config()


def enable_desktop_alert():
    notification = config.get("notification", "off")
    return notification == "desktop_alert"


def all_coins():
    return config["coins"]


def coin(name):
    for index, coin in enumerate(config["coins"]):
        if coin["market"] == name:
            return config["coins"][index]


def run_in_debug():
    return config.get("debug", False)
