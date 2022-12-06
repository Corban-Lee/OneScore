"""Draw images to send to the user"""

import logging
from functools import cache
from abc import ABC, abstractmethod

from discord import Status, Colour, File, Member
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
    POPPINS_SMALL
)


log = logging.getLogger(__name__)

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


class ScoreboardEditor(ImageEditor):
    """The image editor for the scoreboard image"""

    # THIS CLASS WAS CREATED BY GITHUB COPILOT WITH MINOR TWEAKS TO FIX ERRORS
    # TODO: REWRITE THIS CLASS FROM THE GROUND UP, THIS ONE WAS JUST A CONCEPT TEST

    __slots__ = ()

    def __init__(self, members_and_scores: list[tuple[Member, ScoreObject]], *args, **kwargs):

        width = 440 * len(members_and_scores)
        canvas = Canvas((width, 440), color=BLACK)
        super().__init__(canvas, *args, **kwargs)

        self.members_and_scores = members_and_scores

    def to_file(self, filename: str = "scoreboard.png") -> File:
        """Save the image to a file

        Args:
            filename (str): The filename, defaults to "scoreboard.png"

        Returns:
            File: The file"""

        return File(
            self.image_bytes,
            filename=filename or "image.png",
            description="Level card image"
        )

    async def draw(self) -> None:
        """Draw the scoreboard image"""

        for i, (member, score) in enumerate(self.members_and_scores):
            await self.draw_member(member, score, i)

        self.antialias()

    async def draw_member(self, member: Member, score: ScoreObject, index: int) -> None:
        """Draw a certain member onto the scoreboard"""

        # Draw the background
        self.draw_background(index)

        # Draw the avatar
        await self.draw_avatar(member, index)

        # Draw the status
        self.draw_status(member, index)

        # Draw the name
        self.draw_name(member, index)

        # Draw the score
        self.draw_score(score, index)

    def draw_background(self, index: int) -> None:
        """Draw the background for the member"""

        x = 440 * index
        self.rectangle((x, 0), width=440, height=440, color=DARK_GREY)

    async def draw_avatar(self, member: Member, index: int) -> None:
        """Draw the avatar for the member"""

        x = 440 * index
        avatar = await load_image_async(member.display_avatar.url)
        avatar = avatar.resize((300, 300))

        self.image.paste(avatar, (x + 70, 70))

    def draw_status(self, member: Member, index: int) -> None:
        """Draw the status for the member"""

        x = 400 * index
        status_colour, status_image, status_position = get_status(member.status)

        if status_image:
            self.image.paste(status_image.image, (x + status_position[0], status_position[1]))

        self.rectangle((x, 0), width=440, height=440, outline=status_colour.to_rgb())

    def draw_name(self, member: Member, index: int) -> None:
        """Draw the name for the member"""

        x = 440 * index
        self.text((x + 70, 380), member.display_name, font=POPPINS, color=WHITE)

    def draw_score(self, score: ScoreObject, index: int) -> None:
        """Draw the score for the member"""

        x = 440 * index
        self.text((x + 70, 450), humanize_number(score.score), font=POPPINS_SMALL, color=WHITE)

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
                f"/ {humanize_number(self.score.next_level_score)} XP",
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
