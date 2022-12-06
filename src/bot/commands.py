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
from image import ScoreEditor

log = logging.getLogger(__name__)

class CommandsCog(commands.Cog, name="Score Commands"):
    """Cog for level commands"""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

        rank_ctx_menu = app_commands.ContextMenu(
            name="/rank", callback=self._rank_context_menu
        )
        bot.tree.add_command(rank_ctx_menu)

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready"""

        log.info("Cog %s is ready", self.qualified_name)

    async def get_rank(self, member: discord.Member) -> discord.File:
        """Get the rank of the user

        Args:
            inter (Inter): The interaction
            member_id (int): The member id

        Returns:
            discord.File: The rank image
        """

        score = db.field(
            "SELECT score FROM scores "
            "WHERE member_id = ? AND guild_id = ?",
            member.id, member.guild.id
        )

        score_obj = ScoreObject(member.id, member.guild.id, score)
        score_image_editor = ScoreEditor(member, score_obj)
        await score_image_editor.draw()
        return score_image_editor.to_file()

    async def respond_with_rank(self, inter: Inter, member: discord.Member=None):
        """Respond with the rank of the member to an interaction,
        or the user who invoked the interaction if no member is provided

        Args:
            inter (Inter): The interaction
            member (discord.Member, None): The member or NoneType
        """

        member = member or inter.user
        if member.bot:
            await inter.response.send_message("Bots don't have ranks :(")
            return

        # The member object from the interaction doesn't have the status
        # data, so we must get a new member object from the guild
        member = member.guild.get_member(member.id)

        await inter.response.defer(thinking=True)

        rank_image_file = await self.get_rank(member)
        await inter.followup.send(file=rank_image_file)

    @app_commands.command(name="rank")
    async def _rank(self, inter: Inter, member: discord.Member=None):
        """Get the user's rank"""

        await self.respond_with_rank(inter, member)

    @app_commands.command(name="level")
    async def _level(self, inter: Inter, member: discord.Member=None):
        """Get the user's rank | Alias for `/rank`"""

        await self.respond_with_rank(inter, member)

    @app_commands.command(name="score")
    async def _score(self, inter: Inter, member: discord.Member=None):
        """Get the user's score | Alias for `/rank`"""

        await self.respond_with_rank(inter, member)

    async def _rank_context_menu(self, inter: Inter, member: discord.Member=None):
        """Get the user's rank | Context menu command"""

        await self.respond_with_rank(inter, member)

    @commands.command(name="rank", aliases=("level", "score"))
    async def _rank_normal_cmd(self, ctx: commands.Context, member: discord.Member=None):
        """Get the user's rank"""

        member = member or ctx.author
        if member.bot:
            return await ctx.reply("Bots don't have ranks :(")

        rank_image_file = await self.get_rank(member or ctx.author)
        await ctx.reply(file=rank_image_file)

    @commands.command(name="debug-rank-repr")
    async def _debug_rank_repr_cmd(self, ctx: commands.Context, member: discord.Member=None):
        """Get the repr of a rank"""

        member = member or ctx.author
        if member.bot:
            return await ctx.reply("Bots don't have ranks :(")

        score = db.field(
            "SELECT score FROM scores "
            "WHERE member_id = ? AND guild_id = ?",
            member.id, ctx.guild.id
        )

        score_obj = ScoreObject(member.id, ctx.guild.id, score)
        await ctx.reply(repr(score_obj))


async def setup(bot: commands.Bot) -> None:
    """Setup the cog"""

    await bot.add_cog(CommandsCog(bot))
