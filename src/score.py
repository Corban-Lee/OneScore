"""File for handling and calculating scores"""

import logging
from dataclasses import dataclass
from math import sqrt, ceil

from db import db


log = logging.getLogger(__name__)


@dataclass
class ScoreObject:
    """Score object"""

    member_id: int
    guild_id: int
    _score: int

    @property
    def rank(self) -> str:
        """Get the rank of the score

        Returns:
            str: The rank
        """

        return db.field(
            "SELECT rank FROM (SELECT member_id, RANK() OVER "
            "( ORDER BY score DESC ) AS rank FROM scores "
            "WHERE guild_id = ?) WHERE member_id = ?",
            self.guild_id, self.member_id
        )

    @property
    def level(self) -> float:
        """Get the level of the score

        Returns:
            int: The level
        """

        return (0.07 * sqrt(max(self.score, 1))) + 1

    @property
    def score(self) -> int:
        """Get the score obtained in the current level

        Returns:
            int: Score obtained in the current level
        """

        return self.score - self.prev_level_score

    @property
    def total_score(self) -> int:
        """Get the total score

        Returns:
            int: The total score
        """

        return self._score

    @property
    def next_level_score(self) -> float:
        """Get the score required for the next level

        Returns:
            int: The score required for the next level
        """

        return (ceil(self.level - 1) / 0.07) ** 2

    @property
    def prev_level_score(self) -> float:
        """Get the score required for the previous level

        Returns:
            int: The score required for the previous level
        """

        return (ceil(self.level - 2) / 0.07) ** 2

    @property
    def progress(self) -> float:
        """Get the progress to the next level

        Returns:
            float: The progress to the next level
        """

        return (
            self.current_level_score /
            (self.next_level_score - self.prev_level_score)
        ) * 100

    def set_score(self, score: int) -> None:
        """Set the score

        Args:
            score (int): The score
        """

        self._score = score

    def __str__(self) -> str:
        """Get the string representation of the score object

        Returns:
            str: The string representation
        """

        return f"Level {self.level} (#{self.rank})"
