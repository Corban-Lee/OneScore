"""Extension for the bot commands"""

import logging

import discord
from discord import (
    app_commands,
    Interaction as Inter
)
from discord.ext import commands

from db import db
from score import ScoreObject

log = logging.getLogger(__name__)

class CommandsCog(commands.Cog, name="Score Commands"):
    """Cog for level commands"""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready"""

        log.info("Cog %s is ready", self.qualified_name)

    async def get_rank(self, member: discord.Member) -> str:
        """Get the rank of the user

        Args:
            inter (Inter): The interaction
            member_id (int): The member id
        """

        score = db.field(
            "SELECT score FROM scores "
            "WHERE member_id = ? AND guild_id = ?",
            member.id, member.guild.id
        )

        return ScoreObject(member.id, member.guild.id, score)

    async def respond_with_rank(self, inter: Inter, member: discord.Member=None):
        """Respond with the rank of the user to an interaction

        Args:
            inter (Inter): The interaction
            member (discord.Member): The member
        """

        member = member or inter.user

        rank = await self.get_rank(member)
        await inter.response.send_message(f"Your rank is {rank}")

    @app_commands.command(name="rank")
    async def _rank(self, inter: Inter):
        """Get the user's rank"""

        await self.respond_with_rank(inter)

    @app_commands.command(name="level")
    async def _level(self, inter: Inter):
        """Get the user's rank | Alias for `/rank`"""

        await self.respond_with_rank(inter)

    @app_commands.command(name="score")
    async def _score(self, inter: Inter):
        """Get the user's score | Alias for `/rank`"""

        await self.respond_with_rank(inter)

    @commands.command(name="rank", aliases=("level", "score"))
    async def _rank_normal_cmd(self, ctx: commands.Context, member: discord.Member=None):
        """Get the user's rank"""

        member = member or ctx.author
        rank = await self.get_rank(member)
        await ctx.reply(rank)


async def setup(bot: commands.Bot) -> None:
    """Setup the cog"""

    await bot.add_cog(CommandsCog(bot))
