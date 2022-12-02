"""The database initializer"""

from . import db

# Build the database using the build script at data/db/build.sql
db.build()
