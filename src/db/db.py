"""Functions for interacting with the database."""

import logging
from os.path import isfile
from sqlite3 import connect

from constants import DB_PATH, BUILD_PATH


log = logging.getLogger(__name__)

# Connect to the database
conn = connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON;")  # enable foreign keys

log.info("Database connection established")

def with_commit(func):
    """Wrapper to commit changes to the database"""

    def inner(*args, **kwargs):
        func(*args, **kwargs)
        commit()

    return inner

@with_commit
def build():
    """Build the database from the build script"""

    log.debug("Building database")

    if isfile(BUILD_PATH):
        scriptexec(BUILD_PATH)
        return

    raise ValueError('Build script not found')

def commit():
    """Commit changes to the database"""

    log.debug("Committing changes")
    conn.commit()

def close():
    """Close the database connection"""

    log.debug("Closing database connection")
    conn.close()

def field(cmd, *vals):
    """Return a single field"""

    log.debug("Executing command for field: %s, vals:%s", cmd, vals)
    cur.execute(cmd, tuple(vals))

    # If row exists, return the first row
    if (fetch := cur.fetchone()) is not None:
        return fetch[0]

def record(cmd, *vals):
    """Return a single record"""

    log.debug("Executing command for record: %s, vals: %s", cmd, vals)
    cur.execute(cmd, tuple(vals))
    return cur.fetchone()

def records(cmd, *vals):
    """Return all records"""

    log.debug("Executing command for records: %s, vals: %s", cmd, vals)
    cur.execute(cmd, tuple(vals))
    return cur.fetchall()

def column(cmd, *vals):
    """Return a single column"""

    log.debug("Executing command for column: %s, vals: %s", cmd, vals)
    cur.execute(cmd, tuple(vals))
    return [item[0] for item in cur.fetchall()]

def execute(cmd, *vals):
    """Execute a command"""

    log.debug("Executing command: %s, vals: %s", cmd, vals)
    cur.execute(cmd, tuple(vals))
    return cur

def multiexec(cmd, valset):
    """Execute multiple commands"""

    log.debug("Executing multiple commands: %s, valset: %s", cmd, valset)
    cur.executemany(cmd, valset)

def scriptexec(path):
    """Execute a script"""

    log.debug("Executing script: %s", path)
    with open(path, 'r', encoding='utf-8') as script:
        cur.executescript(script.read())
