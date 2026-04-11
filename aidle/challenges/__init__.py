from aidle.challenges.base import BaseChallenge
from aidle.challenges.maze import MazeChallenge

REGISTRY: dict[str, type[BaseChallenge]] = {
    MazeChallenge.slug: MazeChallenge,
}

__all__ = ["BaseChallenge", "MazeChallenge", "REGISTRY"]
