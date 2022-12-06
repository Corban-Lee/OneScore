"""Draw images to send to the user"""

import logging
from functools import cache
from time import perf_counter

from discord import Status, Colour, File
from easy_pil import Editor, Canvas, Text, load_image_async
from PIL import Image

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
def unpack_status(status) -> tuple[Image.Image, Colour]:
    """Get the status image and colour

    Args:
        status (str): The status

    Returns:
        Image: The status image
        Colour: The status colour
    """

    match status:

        case Status.online:
            return Colour.green()

        case Status.idle:
            return Colour.dark_gold()

        case Status.dnd:
            return Colour.red()

        case Status.offline:
            return Colour.light_grey()

        case Status.invisible:
            return Colour.blurple()

        case _:
            raise ValueError(f"Unknown Status: {status}")


class ImageEditor(Editor):
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
        self.canvas = Canvas(self.image)
        self.status_icon, self.status_colour = unpack_status(member.status)

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
        await self._draw_avatar()  # http call for the image
        self._draw_status()
        self.draw_name()
        self.draw_level()
        self.draw_progress()

        # Round the corners and apply antialias
        self.rounded_corners(20)
        self.antialias()

    def draw_background(self):
        """Draw the accent background"""

        self.polygon(
            ((2, 2), (2, 360), (360, 2), (2, 2)),
            fill=self._accent_colour
        )

    async def _draw_avatar(self):
        """Draw the avatar"""

        self.paste(Editor(
            Canvas(
                (320, 320),
                color=BLACK
            )
            ).circle_image().paste(
                Editor(
                    await load_image_async(self.member.avatar_url)
                ).resize((300, 300)).circle_image(),
                (10, 10)
            ),
            (40, 40)
        )

    def _draw_status(self):
        """Draw the status icon"""

        status_image = Editor(Canvas(
            (90, 90),
            color=self._background_1
        )).circle_image().paste(
            Editor(Canvas(
                (70, 70),
                color=self._status_colour
            )).circle_image(),
            (10, 10)
        )

        log.debug("Drawing status icon symbol")

        match self.member.status:

            case Status.idle:
                status_image.paste(Editor(Canvas(
                    (50, 50),
                    color=self._background_1
                )).circle_image(), (5, 10))

            case Status.dnd:
                status_image.rectangle(
                    (20, 39), width=50, height=12,
                    fill=self._background_1, radius=15
                )

            case Status.offline:
                status_image.paste(Editor(Canvas(
                    (40, 40),
                    color=self._background_1
                )).circle_image(), (25, 25))

            case _:
                pass

        # Paste the status icon onto the card
        self.editor.paste(status_image, (260, 260))

    def _draw_progress(self):
        """Draw the progress bar"""

        # Bar dimensions
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
            width=width, height=height,
            color=self.accent_colour,
            radius=radius,
            percentage=max(self.score.progress, 5),
        )

    def _draw_name(self):
        """Draw the name"""

        name = self.member.display_name
        discriminator = f"#{self.member.discriminator}"

        # Prevent the name text from overflowing
        if len(name) > 15:
            log.debug("Name is too long, shortening")
            name = name[:15]

        self.multi_text(
            position=(420, 220),  # bottom left anchor position
            texts=(
                Text(
                    name,
                    font=POPPINS,
                    color=WHITE
                ),
                Text(
                    discriminator,
                    font=POPPINS_SMALL,
                    color=LIGHT_GREY
                )
            )
        )

#     def _draw_exp(self):
#         """Draw the exp and next exp on the card"""

#         start = perf_counter()
#         log.debug("Drawing exp text")

#         # Draw it right onto the card
#         self.editor.multi_text(
#             position=(1740, 225),  # bottom right
#             align="right",
#             texts=(
#                 Text(
#                     self.lvl_obj.xp,
#                     font=POPPINS_SMALL,
#                     color=self._foreground_1
#                 ),
#                 Text(
#                     f"/ {self.lvl_obj.next_xp} XP",
#                     font=POPPINS_SMALL,
#                     color=self._foreground_2
#                 )
#             )
#         )

#         end = perf_counter()
#         log.debug(
#             "Finished drawing exp text in %s seconds",
#             end-start
#         )

#     def _draw_levelrank(self):
#         """Draw the level and rank on the card"""

#         start = perf_counter()
#         log.debug("Drawing level and rank text")

#         self.editor.multi_text(
#             position=(1700, 80),  # top right
#             align="right",
#             texts=(
#                 Text(
#                     "RANK",
#                     font=POPPINS_SMALL,
#                     color=self._foreground_2
#                 ),
#                 Text(
#                     f"#{self.lvl_obj.rank} ",
#                     font=POPPINS,
#                     color=self._accent_colour
#                 ),
#                 Text(
#                     "LEVEL",
#                     font=POPPINS_SMALL,
#                     color=self._foreground_2
#                 ),
#                 Text(
#                     str(self.lvl_obj.level),
#                     font=POPPINS,
#                     color=self._accent_colour
#                 )
#             )
#         )

#         end = perf_counter()
#         log.debug(
#             "Finished drawing level and rank text in %s seconds",
#             end-start
#         )
