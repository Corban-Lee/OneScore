"""Draw images to send to the user"""

import logging
import asyncio
from functools import cache
from abc import ABC, abstractmethod
from threading import Thread, Lock
from math import ceil

from discord import Status, Colour, File, Member, Guild
from easy_pil import Editor, Canvas, Text, load_image_async
from PIL import Image

from utils import humanize_number
from score import ScoreObject
from constants import (
    WHITE,
    BLACK,
    LIGHT_GREY,
    DARK_GREY,
    POPPINS,
    POPPINS_LARGE,
    POPPINS_SMALL,
    COL_WIDTH,
    COL_HEIGHT,
    HEAD_HEIGHT,
    MARGIN,
    SHADOW_OFFSET_X,
    SHADOW_OFFSET_Y
)


log = logging.getLogger(__name__)
lock = Lock()

@cache
def get_status(status, /) -> tuple[Colour, Editor, tuple[int, int]]:
    """Get the status image and colour

    Args:
        status (discord.Status): The status

    Returns:
        Colour: The status colour
        Editor: The status image editor
        Tuple[int, int]: The status image position
    """

    match status:

        case Status.online:
            return Colour.green(), None, None

        case Status.idle:
            return (
                Colour.dark_gold(),
                Editor(Canvas((50, 50), color=BLACK)).circle_image(),
                (5, 10)
            )

        case Status.dnd:
            return (
                Colour.red(),
                Editor(Canvas((50, 12), color=BLACK)).rounded_corners(15),
                (20, 39)
            )

        case Status.offline:
            return (
                Colour.light_grey(),
                Editor(Canvas((40, 40), color=BLACK)).circle_image(),
                (25, 25)
            )

        case Status.invisible:
            return Colour.blurple(), None, None

        case _:
            raise ValueError(f"Unknown Status: {status}")


class ImageEditor(Editor, ABC):
    """An editor for images"""

    @abstractmethod
    async def draw(self) -> None:
        """Draw the image"""

    def to_file(self, filename: str=None) -> File:
        """Save the image to a file

        Args:
            filename (str): The filename, defaults to "image.png"

        Returns:
            File: The file"""

        return File(
            self.image_bytes,
            filename=filename or "image.png",
            description="OneScore Image"
        )

    def antialias(self):
        """Antialias the image, also halves the image size due
        to limitations"""

        self.image = self.image.resize(
            (self.image.width // 2, self.image.height // 2),
            Image.ANTIALIAS
        )


class ScoreboardEditor(ImageEditor, ABC):
    """The image editor for the scoreboard image"""

    __slots__ = ("members_and_scores", )

    COL_WIDTH: int
    COL_HEIGHT: int
    MARGIN: int

    @abstractmethod
    async def draw(self) -> None:
        """Draw the scoreboard image"""

    @abstractmethod
    async def draw_member(self, member: Member, score: ScoreObject) -> Editor:
        """Draw a member's column/row

        Args:
            member (discord.Member): The member
            score (ScoreObject): The score
        """

class GridScoreboardEditor(ScoreboardEditor):
    """The image editor for the grid scoreboard image"""

    __slots__ = ("members_and_scores", )
    MAX_COLS = 6

    def __init__(self, members_and_scores: list[tuple[Member, ScoreObject]]):

        if not members_and_scores:
            raise ValueError("members_and_scores cannot be empty")

        self.members_and_scores = members_and_scores

        width = MARGIN + (
            (COL_WIDTH + MARGIN) *
            min(len(members_and_scores), self.MAX_COLS)
        )
        height = HEAD_HEIGHT + MARGIN + (
            (COL_HEIGHT + MARGIN) *
            ceil(len(members_and_scores) / self.MAX_COLS)
        )

        canvas = Canvas((width, height))
        super().__init__(canvas)

        # Draw the background
        self.rectangle(
            (0, 0), width=width, height=height,
            color=DARK_GREY, outline=LIGHT_GREY,
            stroke_width=5, radius=100
        )

    async def draw(self) -> None:
        """Draw the scoreboard image"""

        log.debug("drawing grid scoreboard")

        # Position of the first column
        x_position = MARGIN
        y_position = HEAD_HEIGHT + MARGIN

        # list of threads and list of thread results
        thread_queue = []
        drawn_members: list[Editor, tuple[int, int]] = []

        def between_callback(position, *args):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            member_image = loop.run_until_complete(self.draw_member(*args))
            loop.close()
            drawn_members.append((member_image, position))

        # iterate over the members and create a new thread of each one
        # each thread will draw the member and append it to the drawn_members list

        for i, (member, score) in enumerate(self.members_and_scores):

            position = (x_position, y_position)
            thread = Thread(target=between_callback, args=(position, member, score))
            thread_queue.append(thread)

            # calculate the position for the next member in the loop

            i += 1  # i is 0 indexed

            # if the current column is the last column, move to the next row
            if i % self.MAX_COLS == 0:
                y_position += COL_HEIGHT + MARGIN
                x_position = MARGIN
                continue

            # otherwise, move to the next column
            x_position += COL_WIDTH + MARGIN

        # start all the threads and wait for them to finish
        for thread in thread_queue:
            thread.start()
        for thread in thread_queue:
            thread.join()

        # paste all completed member images onto the scoreboard
        for member_image, position in drawn_members:
            position = (position[0] + SHADOW_OFFSET_X, position[1])
            self.paste(member_image, position)

        # Draw the header if the scoreboard is wide enough
        if self.image.width > COL_WIDTH * 2:
            await self.draw_header(member.guild)  # pylint: disable=W0631

        # Round the corners and antialias the final image
        self.rounded_corners(20)
        self.antialias()

    async def draw_member(self, member: Member, score: ScoreObject) -> Editor:
        """Draw a certain member onto the scoreboard"""

        log.debug("drawing member %s", member)

        # Create an editor for the member column
        width = COL_WIDTH + (SHADOW_OFFSET_X * -1)
        height = COL_HEIGHT + SHADOW_OFFSET_Y
        member_column = MemberColumn(member, score, (width, height))
        await member_column.draw()

        return member_column

    async def draw_header(self, guild:Guild) -> None:
        """Draw the footer"""

        title_cordinates = (MARGIN, MARGIN + 35)

        if guild.icon:
            guild_icon = await load_image_async(guild.icon.url)
            guild_icon = Editor(guild_icon.resize((150, 150))).circle_image()
            self.paste(guild_icon, (MARGIN, MARGIN))
            title_cordinates = (150 + (MARGIN * 2), title_cordinates[1])

        self.text(
            title_cordinates,
            f"{guild.name}",
            font=POPPINS_LARGE,
            color=WHITE,
            align="left"
        )

        member_count_cordinates = (self.image.width - MARGIN, title_cordinates[1] + 10)

        self.text(
            member_count_cordinates,
            f"Showing {len(self.members_and_scores)} of {guild.member_count} members",
            font=POPPINS_SMALL,
            color=WHITE,
            align="right"
        )

class MemberColumn(ImageEditor):
    """A class to draw a member column"""

    __slots__ = ("member", "score", "accent_colour")

    def __init__(self, member: Member, score: ScoreObject, size: tuple[int, int]):

        self.member = member
        self.score = score
        self.size = size

        # Default to a light grey accent colour if the member has no colour
        if member.colour == Colour.default():
            self.accent_colour = Colour.light_grey().to_rgb()
        else:
            self.accent_colour = member.colour.to_rgb()

        canvas = Canvas(size)
        super().__init__(canvas)

    async def draw(self):
        """Draw the member column"""

        self.draw_background()
        self.draw_name()
        self.draw_level()
        await self.draw_avatar()

    def draw_background(self) -> None:
        """Draw the background for the member"""

        drop_shadow = Editor(Canvas((COL_WIDTH, COL_HEIGHT), color="#0F0F0F80"))
        drop_shadow.rounded_corners(15)
        drop_shadow_postion = (0, SHADOW_OFFSET_Y)
        self.paste(drop_shadow, drop_shadow_postion)

        background = Editor(Canvas((COL_WIDTH, COL_HEIGHT), color=BLACK))
        background.rectangle((0, 0), color=self.accent_colour, width=COL_WIDTH, height=175)
        background.rounded_corners(15)

        self.paste(background, (10, 0))

    async def draw_avatar(self) -> None:
        """Draw the avatar for the member"""

        size = COL_WIDTH - int(MARGIN * 2.5)
        avatar_position = (
            (COL_WIDTH // 2) - (size // 2) + (SHADOW_OFFSET_X * -1),
            int(MARGIN * 0.8)
        )

        avatar = Editor(Canvas((size, size), color=BLACK)).circle_image()
        avatar.paste(
            Editor(
                await load_image_async(self.member.display_avatar.url)
            ).resize((size - 20, size - 20)).circle_image(),
            position=(10, 10)
        )

        self.paste(
            Editor(avatar).circle_image(),
            avatar_position
        )

    def draw_name(self) -> None:
        """Draw the name for the member"""

        name = self.member.display_name

        # Prevent the name text from overflowing
        if len(name) > 15:
            log.debug("name is too long, shortening")
            name = name[:15]

        text_position = ((SHADOW_OFFSET_X * -1) + (COL_WIDTH // 2), 380)

        self.text(
            text_position, name, font=POPPINS_SMALL, color=WHITE, align="center"
        )

    def draw_level(self) -> None:
        """Draw the level for the member"""

        # We need the GIL to prevent a reccursion error
        with lock:

            rank_position = ((SHADOW_OFFSET_X*-1) + (COL_WIDTH // 2), 470)
            self.multi_text(
                rank_position,
                texts=(
                    Text("RANK #", font=POPPINS_SMALL, color=LIGHT_GREY),
                    Text(str(self.score.rank), font=POPPINS_SMALL, color=WHITE)
                ),
                align="center",
                space_separated=False
            )

        level_position = (rank_position[0], 520)
        self.text(
            level_position, f"LEVEL {int(self.score.level)}",
            font=POPPINS_SMALL, color=LIGHT_GREY, align="center"
        )


class ScoreEditor(ImageEditor):
    """The image editor for the score image"""

    __slots__ = ("member", "accent_colour")

    def __init__(self, member: Member, score_object: ScoreObject, *args, **kwargs):
        super().__init__(
            Canvas((1800, 400), color=BLACK),
            *args, **kwargs
        )

        self.member = member
        self.score = score_object

        self.accent_colour = self.member.colour
        if self.accent_colour == Colour.default():
            self.accent_colour = Colour.blurple()

        self.accent_colour = self.accent_colour.to_rgb()

    def antialias(self):
        """Antialias the image, also halves the image size due
        to limitations"""

        self.image = self.image.resize(
            (self.image.width // 2, self.image.height // 2),
            Image.ANTIALIAS
        )

    async def draw(self) -> None:
        """Draw the entire image, call this to actually create the image"""

        # Draw all of the separate image components
        self.draw_background()
        await self.draw_avatar()
        self.draw_status()
        self.draw_name()
        self.draw_level()
        self.draw_score()
        self.draw_progress()

        # Smooth the corners
        self.rounded_corners(20)

        # Antialias the image | also halves the image size due to limitations
        self.antialias()

    def draw_background(self):
        """Draws an accent polygon on the background"""

        self.polygon(
            ((2, 2), (2, 360), (360, 2), (2, 2)),
            fill=self.accent_colour
        )

    async def draw_avatar(self):
        """Draw the avatar with a thin black circle around it"""

        log.debug("drawing avatar")

        avatar = await load_image_async(self.member.display_avatar.url)
        avatar_image = Editor(avatar).resize((300, 300)).circle_image()

        avatar_image_container = Editor(Canvas((320, 320), color=BLACK)).circle_image()
        avatar_image_container.paste(avatar_image, (10, 10))

        self.paste(avatar_image_container, (40, 40))

    def draw_status(self):
        """Draw the status icon over the avatar image"""

        # Get the colour and icons for the status
        status_colour, status_icon, status_icon_position = get_status(self.member.status)

        status_image = Editor(Canvas((90, 90), color=BLACK)).circle_image()
        status_image.paste(
            Editor(Canvas((70, 70), color=status_colour.to_rgb())).circle_image(),
            (10, 10)
        )

        # Paste the status icon onto the card if applicable (idle, dnd, offline)
        if status_icon:
            status_image.paste(status_icon, status_icon_position)

        self.paste(status_image, (260, 260))

    def draw_progress(self):
        """Draw the progress bar across the image"""

        log.debug("drawing progress bar")

        progress = self.score.progress
        position = (420, 275)
        width = 1320
        height = 60
        radius = 40

        # The trough/background of the progress bar
        self.rectangle(
            position=position,
            width=width, height=height,
            color=DARK_GREY,
            radius=radius
        )

        # The actual progress bar
        # Only draw if there is progress, otherwise it looks weird
        if progress > 0:
            self.bar(
                position=position,
                max_width=width, height=height,
                color=self.accent_colour,
                radius=radius,
                percentage=max(progress, 5),
            )

    def draw_name(self):
        """Draw the member's name and discriminator on the image"""

        log.debug("drawing name text")

        name = self.member.display_name
        discriminator = f"#{self.member.discriminator}"

        # Prevent the name text from overflowing
        if len(name) > 15:
            log.debug("name is too long, shortening")
            name = name[:15]

        texts = (
            Text(name, font=POPPINS, color=WHITE),
            Text(discriminator, font=POPPINS_SMALL, color=LIGHT_GREY)
        )
        self.multi_text(
            position=(420, 220),
            texts=texts
        )

    def draw_score(self):
        """Draw the score and score to reach the next level on the image"""

        log.debug("drawing score text")

        texts = (
            Text(humanize_number(self.score.score), font=POPPINS_SMALL, color=WHITE),
            Text(
                f"/ {humanize_number(self.score.next_level_score-self.score.total_score)} XP",
                font=POPPINS_SMALL, color=LIGHT_GREY
            )
        )
        self.multi_text(
            position=(1740, 225),
            align="right",
            texts=texts
        )

    def draw_level(self):
        """Draw the level number and rank number on the image"""

        log.debug("drawing level and rank text")

        texts = (
            Text("RANK", font=POPPINS_SMALL, color=LIGHT_GREY),
            Text(f"#{self.score.rank} ", font=POPPINS, color=self.accent_colour),
            Text(" LEVEL", font=POPPINS_SMALL, color=LIGHT_GREY),
            Text(humanize_number(self.score.level), font=POPPINS, color=self.accent_colour)
        )
        self.multi_text(
            position=(1700, 80),
            align="right",
            texts=texts
        )
