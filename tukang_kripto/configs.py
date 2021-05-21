import json


def read_config():
    f = open("config.json")
    return json.load(f)


config = read_config()


def enable_desktop_alert():
    return config['notification'] == 'desktop_alert'


def all_coins():
    return config['coins']


def coin(name):
    for index, coin in enumerate(config['coins']):
        if coin["market"] == name:
            return config['coins'][index]
