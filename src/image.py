"""Draw images to send to the user"""

import logging
from functools import cache
from time import perf_counter
from abc import ABC, abstractmethod

from discord import Status, Colour, File
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
        pass

    @abstractmethod
    def to_file(self) -> File:
        """Create and return a discord.File of the image"""
        pass


class ScoreEditor(ImageEditor):
    """The image editor"""

    __slots__ = (
        "canvas", "member", "accent_colour", "status_icon", "status_colour"
    )

    def __init__(self, member, score_object: ScoreObject, *args, **kwargs):
        super().__init__(
            Canvas((1800, 400), color=BLACK),
            *args, **kwargs
        )

        self.member = member
        self.score = score_object
        self.canvas = Canvas(self.image.size)
        self.status_colour, self.status_editor, self.status_pos = get_status(member.status)

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

    async def draw(self):
        """Draw the image"""

        # Draw the image
        self.draw_background()
        await self.draw_avatar()  # http call for the image
        self.draw_status()
        self.draw_name()
        self.draw_level()
        self.draw_score()
        self.draw_progress()

        # Round the corners and apply antialias
        self.rounded_corners(20)
        self.antialias()

    def draw_background(self):
        """Draw the accent background"""

        self.polygon(
            ((2, 2), (2, 360), (360, 2), (2, 2)),
            fill=self.accent_colour
        )

    async def draw_avatar(self):
        """Draw the avatar"""

        self.paste(Editor(
            Canvas(
                (320, 320),
                color=BLACK
            )
            ).circle_image().paste(
                Editor(
                    await load_image_async(self.member.display_avatar.url)
                ).resize((300, 300)).circle_image(),
                (10, 10)
            ),
            (40, 40)
        )

    def draw_status(self):
        """Draw the status icon"""

        status_image = Editor(Canvas(
            (90, 90),
            color=BLACK
        )).circle_image().paste(
            Editor(Canvas(
                (70, 70),
                color=self.status_colour.to_rgb()
            )).circle_image(),
            (10, 10)
        )

        if self.status_editor:
            status_image.paste(self.status_editor, self.status_pos)

        # Paste the status icon onto the card
        self.paste(status_image, (260, 260))

    def draw_progress(self):
        """Draw the progress bar"""

        log.debug("drawing progress bar")

        position = (420, 275)
        width = 1320
        height = 60
        radius = 40

        self.rectangle(
            position=position,
            width=width, height=height,
            color=DARK_GREY,
            radius=radius
        )

        self.bar(
            position=position,
            max_width=width, height=height,
            color=self.accent_colour,
            radius=radius,
            percentage=max(self.score.progress, 5),
        )

    def draw_name(self):
        """Draw the name"""

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
        """Draw the exp and next exp on the card"""

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
        """Draw the level and rank on the card"""

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
