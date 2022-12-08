"""Draw images to send to the user"""

import logging
import asyncio
from functools import cache
from abc import ABC, abstractmethod
from threading import Thread, Lock

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
    POPPINS_SMALL,
    POPPINS_XSMALL
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

    @abstractmethod
    def to_file(self) -> File:
        """Create and return a discord.File of the image"""


class ListScoreboardEditor(ImageEditor):
    """The image editor for the list scoreboard image"""

    __slots__ = ("members_and_scores", )
    COL_WIDTH = 3250
    COL_HEIGHT = 300
    MARGIN = 60

    def __init__(self, members_and_scores: list[tuple[Member, ScoreObject]], *args, **kwargs):

        if not members_and_scores:
            raise ValueError("members_and_scores cannot be empty")

        width = self.COL_WIDTH + (self.MARGIN * 2)
        height = ((self.COL_HEIGHT + self.MARGIN) * len(members_and_scores)) + self.MARGIN

        canvas = Canvas((width, height))
        super().__init__(canvas, *args, **kwargs)

        self.rectangle(
            (0, 0), width, height, color=DARK_GREY, outline=LIGHT_GREY, stroke_width=5, radius=20
        )

        self.members_and_scores = members_and_scores

    def to_file(self, filename: str=None) -> File:
        """Save the image to a file

        Args:
            filename (str): The filename, defaults to "scoreboard.png"

        Returns:
            File: The file"""

        return File(
            self.image_bytes,
            filename=filename or "scoreboard.png",
            description="Level card image"
        )

    async def draw(self) -> None:
        """Draw the scoreboard image"""

        log.debug("drawing scoreboard image")

        x_position = y_position = self.MARGIN
        queue = []
        done = []

        def between_callback(position, *args):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            member_image = loop.run_until_complete(self.draw_member(*args))
            loop.close()
            done.append((member_image, position))

        for i, (member, score) in enumerate(self.members_and_scores):

            # await self.draw_member(member, score, (x_position, y_position))
            queue.append(
                Thread(
                    target=between_callback,
                    args=((x_position, y_position), member, score)
                )
            )

            log.debug("determining position for next member")

            i += 1  # offset by 1 to account for 0 index

            y_position += self.COL_HEIGHT + self.MARGIN

            log.debug("position determined to be (%s, %s)", x_position, y_position)

        for thread in queue:
            thread.start()

        for thread in queue:
            thread.join()

        for member_image, position in done:
            self.paste(member_image, (position[0], position[1]))

        self.rounded_corners(20)
        self.antialias()

    async def draw_member(self, member: Member, score: ScoreObject) -> None:
        """Draw a certain member onto the scoreboard"""

        log.debug("drawing member %s", member)

        member_editor = Editor(Canvas((self.COL_WIDTH, self.COL_HEIGHT)))

        self.draw_background(member_editor, member.colour)
        await self.draw_avatar(member_editor, member)
        # self.draw_name(member_editor, member)
        # self.draw_level(member_editor, score)

        return member_editor

    def draw_background(self, editor: Editor, accent_colour:Colour) -> None:
        """Draw the background for the member"""

        if accent_colour == Colour.default():
            accent_colour = Colour.light_grey()

        accent_colour = accent_colour.to_rgb()
        accent_size = 270

        background = Editor(Canvas((self.COL_WIDTH, self.COL_HEIGHT), color=BLACK))
        background.polygon(
            (
                # order: top left, bottom left, bottom right, top right
                (accent_size, 0),
                ((accent_size // 2), accent_size // 2),
                (0, accent_size),
                (0, 0)
            ),
            color=accent_colour
        )
        background.rounded_corners(30)
        editor.paste(background, (0, 0))

    async def draw_avatar(self, editor: Editor, member: Member) -> None:
        """Draw the avatar for the member"""

        size = int(self.COL_HEIGHT * 0.8)

        avatar = await load_image_async(member.display_avatar.url)
        avatar = avatar.resize((size, size))

        position = (self.COL_HEIGHT - size) // 2

        editor.paste(
            Editor(avatar).circle_image(),
            (position, position)
        )

    def draw_name(self, editor: Editor, member: Member) -> None:
        """Draw the name for the member"""

        name = member.display_name
        discriminator = f"#{member.discriminator}"

        # Prevent the name text from overflowing
        if len(name) > 15:
            log.debug("name is too long, shortening")
            name = name[:15]

        text_position = (10 + (self.COL_WIDTH // 2), self.COL_HEIGHT - 125)

        editor.text(
            text_position, name + discriminator, font=POPPINS_XSMALL, color=WHITE, align="center"
        )

    def draw_level(self, editor: Editor, score: ScoreObject) -> None:
        """Draw the level for the member"""

        lock.acquire(True, timeout=5)

        level_position = (10 + (self.COL_WIDTH // 2), self.COL_HEIGHT - 70)
        editor.text(
            level_position, f"#{score.rank}", font=POPPINS_SMALL, color=WHITE, align="center"
        )

        lock.release()

    def antialias(self):
        """Antialias the image, also halves the image size due
        to limitations"""

        self.image = self.image.resize(
            (self.image.width // 2, self.image.height // 2),
            Image.ANTIALIAS
        )

    def antialias(self):
        """Antialias the image, also halves the image size due
        to limitations"""

        self.image = self.image.resize(
            (self.image.width // 2, self.image.height // 2),
            Image.ANTIALIAS
        )



class GridScoreboardEditor(ImageEditor):
    """The image editor for the grid scoreboard image"""

    __slots__ = ("members_and_scores", )
    COL_WIDTH = 400
    COL_HEIGHT = 400
    HEAD_HEIGHT = 200
    MARGIN = 60
    MAX_COLS = 6
    SHADOW_OFFSET = (-10, 15)

    def __init__(self, members_and_scores: list[tuple[Member, ScoreObject]], *args, **kwargs):

        if not members_and_scores:
            raise ValueError("members_and_scores cannot be empty")

        width = self.MARGIN + (
            (self.COL_WIDTH + self.MARGIN) * min(len(members_and_scores), self.MAX_COLS)
        )
        height = self.HEAD_HEIGHT + self.MARGIN + (
            (self.COL_HEIGHT + self.MARGIN) * (len(members_and_scores) // self.MAX_COLS)
        )

        canvas = Canvas((width, height))
        super().__init__(canvas, *args, **kwargs)

        self.rectangle(
            (0, 0), width, height, color=DARK_GREY, outline=LIGHT_GREY, stroke_width=5, radius=20
        )

        self.members_and_scores = members_and_scores

    def to_file(self, filename: str=None) -> File:
        """Save the image to a file

        Args:
            filename (str): The filename, defaults to "scoreboard.png"

        Returns:
            File: The file"""

        return File(
            self.image_bytes,
            filename=filename or "scoreboard.png",
            description="Level card image"
        )

    async def draw(self) -> None:
        """Draw the scoreboard image"""

        log.debug("drawing scoreboard image")

        x_position = self.MARGIN
        y_position = self.HEAD_HEIGHT + self.MARGIN
        queue = []
        done = []

        def between_callback(position, *args):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            member_image = loop.run_until_complete(self.draw_member(*args))
            loop.close()
            done.append((member_image, position))

        for i, (member, score) in enumerate(self.members_and_scores):

            # await self.draw_member(member, score, (x_position, y_position))
            queue.append(
                Thread(
                    target=between_callback,
                    args=((x_position, y_position), member, score)
                )
            )

            log.debug("determining position for next member")

            i += 1  # offset by 1 to account for 0 index

            if i % self.MAX_COLS == 0:
                y_position += self.COL_HEIGHT + self.MARGIN
                x_position = self.MARGIN
                continue

            x_position += self.COL_WIDTH + self.MARGIN

            log.debug("position determined to be (%s, %s)", x_position, y_position)

        for thread in queue:
            thread.start()

        for thread in queue:
            thread.join()

        for member_image, position in done:

            print(member_image.image.size)
            self.paste(member_image, (position[0]-10, position[1]))

        if self.image.width > self.COL_WIDTH * 2:
            await self.draw_header(member.guild)  # pylint: disable=undefined-loop-variable

        self.rounded_corners(20)
        self.antialias()

    async def draw_member(self, member: Member, score: ScoreObject) -> None:
        """Draw a certain member onto the scoreboard"""

        log.debug("drawing member %s", member)

        member_editor = Editor(Canvas((self.COL_WIDTH + 10, self.COL_HEIGHT + 15)))

        self.draw_background(member_editor, member.colour)
        await self.draw_avatar(member_editor, member)
        self.draw_name(member_editor, member)
        self.draw_level(member_editor, score)

        return member_editor

    async def draw_header(self, guild:Guild) -> None:
        """Draw the footer"""

        title_cordinates = (self.MARGIN, self.MARGIN + 25)

        if guild.icon:
            guild_icon = await load_image_async(guild.icon.url)
            guild_icon = Editor(guild_icon.resize((100, 100))).circle_image()
            self.paste(guild_icon, (self.MARGIN, self.MARGIN))
            title_cordinates = (100 + (self.MARGIN * 2), title_cordinates[1])

        self.text(
            title_cordinates,
            f"{guild.name}",
            font=POPPINS,
            color=WHITE,
            align="left"
        )

        member_count_cordinates = (self.image.width - self.MARGIN, title_cordinates[1] + 10)

        self.text(
            member_count_cordinates,
            f"Showing {len(self.members_and_scores)} of {guild.member_count} members",
            font=POPPINS_SMALL,
            color=WHITE,
            align="right"
        )

    def draw_background(self, editor: Editor, accent_colour:Colour) -> None:
        """Draw the background for the member"""

        if accent_colour == Colour.default():
            accent_colour = Colour.light_grey()

        accent_colour = accent_colour.to_rgb()

        accent_size = 100

        drop_shadow = Editor(Canvas((self.COL_WIDTH, self.COL_HEIGHT), color="#0F0F0F80"))
        drop_shadow.rounded_corners(15)
        drop_shadow_postion = (0, 15)
        editor.paste(drop_shadow, drop_shadow_postion)

        # self.rectangle(position, self.COL_WIDTH, self.COL_HEIGHT, color=DARK_GREY, radius=15)
        background = Editor(Canvas((self.COL_WIDTH, self.COL_HEIGHT), color=BLACK))
        background.polygon(
            (
                # order: top left, bottom left, bottom right, top right
                (self.COL_WIDTH - accent_size, 0),
                (self.COL_WIDTH - (accent_size // 2), accent_size // 2),
                (self.COL_WIDTH, accent_size),
                (self.COL_WIDTH, 0)
            ),
            color=accent_colour
        )
        background.rounded_corners(15)

        editor.paste(background, (10, 0))

    async def draw_avatar(self, editor: Editor, member: Member) -> None:
        """Draw the avatar for the member"""

        avatar = await load_image_async(member.display_avatar.url)
        avatar = avatar.resize((220, 220))

        avatar_position = (
            (self.COL_WIDTH // 2) - (avatar.width // 2) + 10,  # drop shadow offset
            (self.COL_HEIGHT // 2) - ((avatar.height // 2) + 60)
        )

        editor.paste(
            Editor(avatar).circle_image(),
            avatar_position
        )

    def draw_name(self, editor: Editor, member: Member) -> None:
        """Draw the name for the member"""

        name = member.display_name
        discriminator = f"#{member.discriminator}"

        # Prevent the name text from overflowing
        if len(name) > 15:
            log.debug("name is too long, shortening")
            name = name[:15]

        text_position = (10 + (self.COL_WIDTH // 2), self.COL_HEIGHT - 125)

        editor.text(
            text_position, name + discriminator, font=POPPINS_XSMALL, color=WHITE, align="center"
        )

    def draw_level(self, editor: Editor, score: ScoreObject) -> None:
        """Draw the level for the member"""

        lock.acquire(True, timeout=5)

        level_position = (10 + (self.COL_WIDTH // 2), self.COL_HEIGHT - 70)
        editor.text(
            level_position, f"#{score.rank}", font=POPPINS_SMALL, color=WHITE, align="center"
        )

        lock.release()

    def antialias(self):
        """Antialias the image, also halves the image size due
        to limitations"""

        self.image = self.image.resize(
            (self.image.width // 2, self.image.height // 2),
            Image.ANTIALIAS
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

    def to_file(self, filename: str=None) -> File:
        """Save the image to a file

        Args:
            filename (str): The filename, defaults to "image.png"

        Returns:
            File: The file"""

        return File(
            self.image_bytes,
            filename=filename or "image.png",
            description="Level card image"
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
