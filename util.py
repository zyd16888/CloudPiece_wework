import time


def timestamp2iso(timestamp):
    """
    Convert a timestamp to a ISO 8601 string.
    """
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(timestamp)) + "+08:00"


if __name__ == "__main__":
    print(timestamp2iso(1636941406))
