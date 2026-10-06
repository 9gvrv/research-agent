import os


def clear_terminal():
    # 'nt' indicates Windows; otherwise, it assumes Linux/macOS
    command = "cls" if os.name == "nt" else "clear"
    os.system(command)
