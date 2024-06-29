import re
from typing import Union


def get_duration(time: Union[str, int, float]) -> int:
    """
    Converts a time string in the format of HH:MM:SS, MM:SS, or a numerical value to seconds.
    If the provided time is neither in the correct format nor a numerical value, returns 0.

    Args:
        time: The time value to be converted to seconds. Accepts string, int, or float.

    Returns:
        The converted time value in seconds or 0 if the provided time value is invalid.

    Examples:
        >>> get_duration("12:34:56")
        45296
        >>> get_duration("1:23")
        83
        >>> get_duration("1:20:50")
        4850
        >>> get_duration("123456")
        123456
        >>> get_duration("12:3456")
        0
        >>> get_duration("")
        0
        >>> get_duration(12345)
        12345
        >>> get_duration(123.45)
        123
    """
    if not isinstance(time, (str, int, float)):
        return 0

    if isinstance(time, str):
        if not time:
            return 0

        # Check if the time string is in the format of HH:MM:SS or MM:SS
        time_regex = r"^(?:(\d{1,2}):)?(\d{1,2}):(\d{1,2})$"
        match = re.match(time_regex, time)

        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            return hours * 3600 + minutes * 60 + seconds
        elif time.isdigit():
            # If the time string is a numerical value, parse it as an integer
            return int(time)
    elif isinstance(time, (int, float)):
        # If the time is already a number, return its integer value
        return int(time)

    # If the time is in an invalid format, return 0
    return 0
