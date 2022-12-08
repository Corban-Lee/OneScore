"""Constants for the project"""

DB_PATH = "data/db/db.sqlite"
BUILD_PATH = "data/db/build.sql"

LOGS = 'logs/'
LOG_FILENAME_FORMAT_PREFIX = '%Y-%m-%d %H-%M-%S'
MAX_LOGFILE_AGE_DAYS = 7

from easy_pil import Font

BLACK = "#0F0F0F"
WHITE = "#F9F9F9"
DARK_GREY = "#2F2F2F"
LIGHT_GREY = "#9F9F9F"
POPPINS = Font.poppins(size=70)
POPPINS_SMALL = Font.poppins(size=50)
POPPINS_XSMALL = Font.poppins(size=35)

from enum import Enum, auto

class ScoreboardStyles(Enum):
    Grid = auto()
    List = auto()
