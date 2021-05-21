import json


def read_config():
    f = open("config.json")
    return json.load(f)


def enable_desktop_alert():
    config = read_config()
    return config['notification'] == 'desktop_alert'


def all_coins():
    config = read_config()
    return config['coins']
