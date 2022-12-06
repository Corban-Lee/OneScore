"""
Handle async logging for the project
"""

import sys
import queue
import logging
from logging.handlers import QueueHandler, QueueListener
from datetime import datetime, timedelta
from itertools import count
from typing import TextIO
from pathlib import Path

from constants import (
    LOGS,
    LOG_FILENAME_FORMAT_PREFIX,
    MAX_LOGFILE_AGE_DAYS
)


log = logging.getLogger(__name__)

def _open_file() -> TextIO:
    """
    Returns a file object for the current log file.
    """

    # Create the logs directory if it doesnt exist
    Path(LOGS).mkdir(exist_ok=True)

    # Create a generator to generate a unique filename
    timestamp = datetime.now().strftime(LOG_FILENAME_FORMAT_PREFIX)
    filenames = (
        f'{timestamp}.txt' if i == 0 else f'{timestamp}_({i}).txt' \
            for i in count()
    )

    # Find a filename that doesn't already exist and return it
    for filename in filenames:
        try:
            return (Path(f'{LOGS}/{filename}').open('x', encoding='utf-8'))
        except FileExistsError:
            continue

def _delete_old_logs():
    """
    Search through the logs directory and delete any expired log files.
    The max age in days for log files is defined in src/constants.py
    """

    for path in Path(LOGS).glob('*.txt'):
        prefix = path.stem.split('_')[0]
        try:
            log_date = datetime.strptime(prefix, LOG_FILENAME_FORMAT_PREFIX)
        except ValueError:
            log.warning(f'{path.parent} contains a problematic filename: {path.name}')
            continue

        age = datetime.now() - log_date
        if age >= timedelta(days=MAX_LOGFILE_AGE_DAYS):
            log.info(f'Removing expired log file: {path.name}')
            path.unlink()

def update_log_levels(logger_names:tuple[str], level:int):
    """
    Quick way to update the log level of multiple loggers at once.
    """
    for name in logger_names:
        logger=logging.getLogger(name)
        logger.setLevel(level)

def setup_logs(log_level:int=logging.DEBUG) -> str:
    """
    Setup a logging queue handler and queue listener.
    Also creates a new log file for the current session and deletes old
    log files.
    """

    # Create a queue to pass log records to the listener
    log_queue = queue.Queue()
    queue_handler = QueueHandler(log_queue)

    # Configure the root logger to use the queue
    logging.basicConfig(
        level=log_level,
        handlers=(queue_handler,),
        format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
    )

    file = _open_file()

    # Create handlers for the log output
    file_handler = logging.StreamHandler(file)
    sys_handler = logging.StreamHandler(sys.stdout)

    # Create a listener to handle the queue
    queue_listener = QueueListener(log_queue, file_handler, sys_handler)
    queue_listener.start()

    # Mute loud loggers
    update_log_levels(
        ('discord', 'PIL', 'urllib3', 'aiosqlite'),
        logging.WARNING
    )

    # Clear up old log files
    _delete_old_logs()

    return file.name
