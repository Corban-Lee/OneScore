"""Utilities for the project."""

from math import floor, log as mlog


def humanize_number(number: int|float, /) -> str:
    """Make a long number human readable"""

    if number < 1000:
        return str(floor(number))

    out = int(floor(mlog(number, 1000)))
    suffix = 'KMBT'[out - 1]
    return f'{number / 1000 ** out:.2f}{suffix}'
