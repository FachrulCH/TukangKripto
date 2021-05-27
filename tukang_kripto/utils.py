import csv
import os


def create_alert(title="Hey, there", message="I have something"):
    command = f"""
    osascript -e 'display notification "{message}" with title "{title}"'
    """
    os.system(command)


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
    return "Rp{:,}".format(number)


def filter_by(array, key, value=None):
    # usage: filter_by(data, 'type', 'buy')
    return list(filter(lambda x: x[key] == value, array))


def create_csv_transaction(coin_name, dict_data):
    file = f"transaction_{coin_name.lower()}.csv"
    csv_columns = ["date", "coin_name", "type", "coin_amount", "price"]
    exist = os.path.exists(file)
    if not exist:
        print(f"Creating {file}")
        with open(file, "w+") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=csv_columns)
            writer.writeheader()
            writer.writerow(dict_data)
    else:
        with open(file, "a") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=csv_columns)
            writer.writerow(dict_data)


def get_latest_csv_transaction(coin_name, transaction_type=None):
    file = f"transaction_{coin_name.lower()}.csv"
    with open(file, "r") as csv_file:
        data = csv.reader(csv_file, delimiter=",")
        if transaction_type is not None:
            print("kondisional", transaction_type)
            transactions = [row for row in data if row[2] == transaction_type]
        else:
            transactions = list(data)[1:]
        return transactions[-1]
