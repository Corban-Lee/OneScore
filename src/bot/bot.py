"""The Discord Bot"""

import logging
from datetime import datetime
from os import listdir

import discord
from discord.ext import commands, tasks

from db import db
from .logs import setup_logs

log = logging.getLogger(__name__)


class Bot(commands.Bot):
    """The bot itself"""

    def __init__(self):
        super().__init__(
            command_prefix="os ",
            intents=discord.Intents.all()
        )

        self.start_time = datetime.utcnow()
        setup_logs()

    @tasks.loop(minutes=10)
    async def _autosave_database(self) -> None:
        """Autosave the database every 5 minutes"""

        log.info("Autosaving database...")
        db.commit()

    @property
    async def runtime(self) -> datetime:
        """Get the bot's runtime as a datetime object

        Returns:
            datetime: The bot's runtime
        """

        return datetime.utcnow() - self.start_time

    async def sync_app_commands(self) -> None:
        """Sync application commands"""

        log.info("Syncing application commands...")
        await self.wait_until_ready()
        await self.tree.sync()
        log.info("Application commands synced")

    async def on_ready(self) -> None:
        """When the bot is ready"""

        log.info("Bot ready")
        self._autosave_database.start()  # pylint: disable=E1101
        await self.sync_app_commands()

    async def close(self) -> None:
        """Called when the bot is closing"""

        log.info("Closing bot...")
        db.commit()  # commit changes before closing
        await super().close()

    async def load_extensions(self) -> None:
        """Load all extensions"""

        # Iterate through all files in the ext folder and load them
        for filename in listdir("src/ext"):
            if filename.endswith(".py"):
                await self.load_extension(f"ext.{filename[:-3]}")
