"""The Discord Bot"""

import logging
from datetime import datetime

import discord
from discord.ext import commands, tasks

from db import db
from .logs import setup_logs

log = logging.getLogger(__name__)

class Bot(commands.Bot):
    """The bot itself"""

    __slots__ = ("start_time",)

    def __init__(self):
        super().__init__(
            command_prefix="ob ",
            intents=discord.Intents.all()
        )

        self.start_time = datetime.utcnow()
        setup_logs()

    @tasks.loop(minutes=5)
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
        self._autosave_database.start()
        await self.sync_app_commands()

    async def close(self) -> None:
        """Called when the bot is closing"""

        log.info("Closing bot...")
        db.commit()  # commit changes before closing
        await super().close()

    async def load_extension_from_file(self, filepath: str) -> None:
        """Load an extension

        Args:
            filepath (str): The extension's path
        """

        log.info("Loading extension %s", filepath)
        await self.load_extension(filepath.replace('.py', '').replace('/', '.'))
