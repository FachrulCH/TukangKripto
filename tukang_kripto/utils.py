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
