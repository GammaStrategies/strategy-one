from datetime import datetime


def timestamp_to_date(timestamp):
    """Converts UNIX timestamp to ISO date"""
    return datetime.utcfromtimestamp(timestamp).isoformat()
