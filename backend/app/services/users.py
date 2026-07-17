"""Simple username/password store (prototype — not production auth)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_USERS_PATH = Path(
    __import__("os").getenv("SIM_USERS_PATH", str(_BACKEND_ROOT / "users.json"))
)

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")


def sanitize_username(username: str) -> str:
    return username.strip()


def validate_username(username: str) -> str:
    cleaned = sanitize_username(username)
    if not _USERNAME_RE.match(cleaned):
        raise ValueError(
            "Username must be 3–32 characters: letters, numbers, underscore only."
        )
    return cleaned


def validate_password(password: str) -> str:
    if not isinstance(password, str) or len(password) < 4:
        raise ValueError("Password must be at least 4 characters.")
    return password


def _load_users() -> dict[str, Any]:
    if not _USERS_PATH.is_file():
        return {}
    try:
        data = json.loads(_USERS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_users(users: dict[str, Any]) -> None:
    _USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _USERS_PATH.write_text(json.dumps(users, indent=2) + "\n", encoding="utf-8")


def register_user(username: str, password: str) -> str:
    """Create a user. Returns the stored username. Raises ValueError on conflict."""
    username = validate_username(username)
    password = validate_password(password)
    users = _load_users()
    if username in users:
        raise ValueError(f"Username already exists: {username}")
    users[username] = {
        "password": password,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_users(users)
    return username


def authenticate_user(username: str, password: str) -> str:
    """Verify credentials. Returns username on success."""
    username = validate_username(username)
    password = validate_password(password)
    users = _load_users()
    record = users.get(username)
    if not record or record.get("password") != password:
        raise ValueError("Invalid username or password.")
    return username


def user_exists(username: str) -> bool:
    try:
        username = validate_username(username)
    except ValueError:
        return False
    return username in _load_users()
