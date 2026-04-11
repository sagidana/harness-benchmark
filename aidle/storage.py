from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any


class UserStore:
    """
    Handles per-user JSON persistence.
    Each user gets a single file: <base_dir>/<username>.json
    All I/O is synchronous — files are tiny and writes are infrequent.
    """

    def __init__(self, base_dir: Path | str | None = None) -> None:
        if base_dir is None:
            base_dir = Path.home() / ".aidle" / "users"
        self._dir = Path(base_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, username: str) -> Path:
        # Sanitise: only keep alphanumeric, dash, underscore, dot
        safe = "".join(c for c in username if c.isalnum() or c in "-_.")
        if not safe:
            raise ValueError(f"Invalid username: {username!r}")
        return self._dir / f"{safe}.json"

    def load(self, username: str) -> dict[str, Any] | None:
        """Return the stored user dict, or None if the user doesn't exist yet."""
        path = self._path(username)
        if not path.exists():
            return None
        with path.open() as f:
            return json.load(f)

    def save(self, username: str, data: dict[str, Any]) -> None:
        """Write the user dict to disk (atomic via temp file + rename)."""
        path = self._path(username)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w") as f:
            json.dump(data, f, indent=2)
        tmp.replace(path)

    def get_or_create(self, username: str) -> tuple[dict[str, Any], bool]:
        """
        Load an existing user or create a new one.
        Returns (user_data, created) where created=True means a new user was made.
        """
        data = self.load(username)
        if data is not None:
            return data, False
        data = {
            "username": username,
            "token": secrets.token_hex(16),
            "session": None,
        }
        self.save(username, data)
        return data, True
