import json


def read_config():
    f = open("config.json")
    return json.load(f)


config = read_config()


def enable_desktop_alert():
    return config.get("desktop_alert", False) is True


def enable_notification():
    return config.get("notification", False) is True


def enable_telegram():
    telegram = config.get("telegram", {})
    config_empty = not telegram
    return config_empty is False


def all_coins():
    return config["coins"]


def coin(name):
    for index, coin in enumerate(config["coins"]):
        if coin["market"] == name:
            return config["coins"][index]


def run_in_debug():
    return config.get("debug", False)
