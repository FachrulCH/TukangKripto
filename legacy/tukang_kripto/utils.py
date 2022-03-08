import csv
import os

from tukang_kripto import configs
from tukang_kripto.Telegram import Telegram


def create_alert(title="Hey, there", message="I have something"):
    if configs.enable_desktop_alert():
        command = f"""
        osascript -e 'display notification "{message}" with title "{title}"'
        """
        os.system(command)

    if configs.enable_telegram():
        tele = configs.config["telegram"]
        chat = Telegram(tele["token"], tele["client_id"])
        chat.send(f"{title}: \n{message}")


def print_red(message):
    # print to console with color red
    print(f"\033[91m{message}\033[0m")


def print_green(message):
    # print to console with color red
    print(f"\033[92m{message}\033[0m")


def print_yellow(message):
    # print to console with color red
    print(f"\033[93m{message}\033[0m")


def in_rupiah(number):
    if number:
        return "Rp{:,}".format(int(number))
    return "Rp0"


def filter_by(array, key, value=None):
    # usage: filter_by(data, 'type', 'buy')
    return list(filter(lambda x: x[key] == value, array))


def create_csv_transaction(coin_name, dict_data=None):
    if "/" in coin_name:
        coin_name = coin_name.split("/")[0]
    file = f"transaction_{coin_name.lower()}.csv"
    csv_columns = ["date", "coin_name", "type", "coin_amount", "price", "amount"]
    exist = os.path.exists(file)
    if not exist:
        print(f"Creating {file}")
        with open(file, "w+") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=csv_columns)
            writer.writeheader()
            if dict_data:
                writer.writerow(dict_data)
    else:
        with open(file, "a") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=csv_columns)
            if dict_data:
                writer.writerow(dict_data)


def get_latest_csv_transaction(coin_name, transaction_type=None):
    if "/" in coin_name:
        coin_name = coin_name.split("/")[0]
    file = f"transaction_{coin_name.lower()}.csv"
    with open(file, "r") as csv_file:
        data = csv.reader(csv_file, delimiter=",")
        if transaction_type is not None:
            transactions = [row for row in data if row[2] == transaction_type]
        else:
            transactions = list(data)[1:]

        if len(transactions) > 0:
            return transactions[-1]
        else:
            return transactions
