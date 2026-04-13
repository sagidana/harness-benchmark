from aidle.challenges.base import BaseChallenge
from aidle.challenges.file_editor import FileEditorChallenge
from aidle.challenges.haystack import HaystackChallenge
from aidle.challenges.maze import MazeChallenge

REGISTRY: dict[str, type[BaseChallenge]] = {
    MazeChallenge.slug: MazeChallenge,
    FileEditorChallenge.slug: FileEditorChallenge,
    HaystackChallenge.slug: HaystackChallenge,
}

__all__ = ["BaseChallenge", "FileEditorChallenge", "HaystackChallenge", "MazeChallenge", "REGISTRY"]
