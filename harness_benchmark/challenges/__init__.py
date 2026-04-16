from harness_benchmark.challenges.base import BaseChallenge
from harness_benchmark.challenges.file_editor import FileEditorChallenge
from harness_benchmark.challenges.haystack import HaystackChallenge
from harness_benchmark.challenges.log_investigator import LogInvestigatorChallenge
from harness_benchmark.challenges.maze import MazeChallenge

REGISTRY: dict[str, type[BaseChallenge]] = {
    MazeChallenge.slug: MazeChallenge,
    FileEditorChallenge.slug: FileEditorChallenge,
    HaystackChallenge.slug: HaystackChallenge,
    LogInvestigatorChallenge.slug: LogInvestigatorChallenge,
}

__all__ = ["BaseChallenge", "FileEditorChallenge", "HaystackChallenge", "LogInvestigatorChallenge", "MazeChallenge", "REGISTRY"]
