"""Extension for the bot commands"""

import logging
import sqlite3

import discord
from discord.ext import commands
from discord.utils import get

from db import db

log = logging.getLogger(__name__)


class ListenersCog(commands.Cog, name="Event Listeners"):
    """Cog for level commands"""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    def add_member(self, member_id: int, guild_id: int) -> None:
        """Add a member to the database

        Args:
            member_id (int): The member's ID
            guild_id (int): The guild's ID
        """

        log.debug("Adding member %s to the database", member_id)
        try:
            db.execute(
                "INSERT INTO scores (member_id, guild_id) VALUES (?, ?)",
                member_id, guild_id
            )
        except sqlite3.IntegrityError:
            log.debug("Activating existing member %s", member_id)
            db.execute(
                "UPDATE scores SET active = 1 "
                "WHERE member_id = ? AND guild_id = ?",
                member_id, guild_id
            )

    def add_guild_members(self, guild_id) -> None:
        """Add all members in a guild to the database

        Args:
            guild_id (int): The guild's ID
        """

        log.debug("Adding all members in guild %s to the database", guild_id)
        guild = self.bot.get_guild(guild_id)
        for member in guild.members:
            self.add_member(member.id, guild_id)

    def add_all_members(self) -> None:
        """Add all members in all guilds to the database"""

        log.debug("Adding all members in all guilds to the database")
        for guild in self.bot.guilds:
            self.add_guild_members(guild.id)

    def remove_member(self, member_id: int, guild_id: int) -> None:
        """Deactivate a member in the database

        Args:
            member_id (int): The member's ID
            guild_id (int): The guild's ID
        """

        log.debug("Deactivating member %s from the database", member_id)
        db.execute(
            "UPDATE scores SET active = 0 "
            "WHERE member_id = ? AND guild_id = ?",
            member_id, guild_id
        )

    def remove_guild_members(self, guild_id: int) -> None:
        """Deactivate all members in a guild in the database

        Args:
            guild_id (int): The guild's ID
        """

        log.debug("Deactivating all members in guild %s from the database", guild_id)
        db.execute(
            "UPDATE scores SET active = 0 "
            "WHERE guild_id = ?",
            guild_id
        )

    async def validate_existing_members(self) -> None:
        """Validates members in database are in the assigned guild"""

        log.debug("Validating all members in the database")

        members_data = db.records("SELECT member_id, active FROM scores")

        for member_id, active in members_data:
            for guild in self.bot.guilds:

                log.debug("checking guild %s", guild.name)
                member_exists = bool(get(guild.members, id=member_id))

                # If the member is in the guild and not active - reactivate them
                if member_exists and not active:
                    log.debug("activating member %s", member_id)
                    db.execute(
                        "UPDATE scores SET active = 1 "
                        "WHERE member_id = ? AND guild_id = ?",
                        member_id, guild.id
                    )

                # If the member is NOT in the guild and active - deactivate them
                elif not member_exists and active:
                    log.debug("deactivating member %s", member_id)
                    db.execute(
                        "UPDATE scores SET active = 0 "
                        "WHERE member_id = ? AND guild_id = ?",
                        member_id, guild.id
                    )

                else:
                    log.debug("not changing anything for member %s", member_id)

    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        """When a member joins a guild"""

        if not member.bot:
            self.add_member(member.id, member.guild.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member) -> None:
        """When a member leaves a guild"""

        self.remove_member(member.id, member.guild.id)

    @commands.Cog.listener()
    async def on_guild_join(self, guild) -> None:
        """When the bot joins a guild"""

        self.add_guild_members(guild.id)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild) -> None:
        """When the bot leaves a guild"""

        self.remove_guild_members(guild.id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """When a message is sent"""

        if message.author.bot:
            return

        log.debug("Adding score to member %s", message.author.id)
        db.execute(
            "UPDATE scores SET score = score + 30 "
            "WHERE member_id = ? AND guild_id = ?",
            message.author.id, message.guild.id
        )

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready"""

        log.info("Cog %s is ready", self.qualified_name)
        await self.bot.wait_until_ready()
        await self.validate_existing_members()
        self.add_all_members()


async def setup(bot: commands.Bot) -> None:
    """Setup the cog"""

    await bot.add_cog(ListenersCog(bot))
