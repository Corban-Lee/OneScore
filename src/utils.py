"""Utilities for the project."""

from math import floor, log as mlog


def humanize_number(number: int|float, /, whole: bool=False) -> str:
    """Make a long number human readable

    Args:
        number (int, float): the number to make human readable
        whole (bool): return the number as whole number
    """

    if number < 1000:
        return str(floor(number))

    out = int(floor(mlog(number, 1000)))
    suffix = 'KMBT'[out - 1]

    if whole:  # not happy with this repetition
        return f'{number / 1000 ** out:.0f}{suffix}'

    return f'{number / 1000 ** out:.2f}{suffix}'
