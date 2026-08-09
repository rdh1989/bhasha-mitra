"""Authentication persistence and password handling for Bhasha Mitra."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DB_PATH = Path("data") / "bhasha_mitra.db"
PBKDF2_ITERATIONS = 310_000


@dataclass(frozen=True)
class User:
    id: int
    username: str
    role: str
    is_active: bool


class UserRepository:
    """Small SQLite repository for local application users."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.commit()

        self._ensure_default_users()

    def _ensure_default_users(self) -> None:
        """Create the initial local accounts when they do not already exist.

        Existing users are never overwritten, so changing the environment
        defaults does not unexpectedly change an existing account password or role.
        """
        default_users = [
            (
                os.getenv("BHASHA_ADMIN_USERNAME", "admin").strip(),
                os.getenv("BHASHA_ADMIN_PASSWORD", "admin123"),
                "admin",
            ),
            (
                os.getenv("BHASHA_USER_USERNAME", "user").strip(),
                os.getenv("BHASHA_USER_PASSWORD", "user123"),
                "user",
            ),
            (
                os.getenv("BHASHA_OWNER_USERNAME", "owner").strip(),
                os.getenv("BHASHA_OWNER_PASSWORD", "owner123"),
                "owner",
            ),
        ]

        with self._connect() as connection:
            for username, password, role in default_users:
                if not username or not password:
                    continue

                existing = connection.execute(
                    "SELECT id FROM users WHERE username = ?",
                    (username,),
                ).fetchone()
                if existing:
                    continue

                password_hash, salt = hash_password(password)
                connection.execute(
                    """
                    INSERT INTO users (username, password_hash, password_salt, role)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, password_hash, salt, role),
                )

            connection.commit()

    def authenticate(self, username: str, password: str) -> User | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, username, password_hash, password_salt, role, is_active
                FROM users
                WHERE username = ?
                """,
                (username.strip(),),
            ).fetchone()

        if not row or not bool(row["is_active"]):
            return None

        if not verify_password(password, row["password_hash"], row["password_salt"]):
            return None

        return User(
            id=row["id"],
            username=row["username"],
            role=row["role"],
            is_active=bool(row["is_active"]),
        )

    def get_by_id(self, user_id: int) -> User | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, username, role, is_active FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()

        if not row or not bool(row["is_active"]):
            return None

        return User(
            id=row["id"],
            username=row["username"],
            role=row["role"],
            is_active=bool(row["is_active"]),
        )


def hash_password(password: str) -> tuple[str, str]:
    """Return a PBKDF2-HMAC-SHA256 password hash and random salt."""
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return derived.hex(), salt.hex()


def verify_password(password: str, expected_hash: str, salt: str) -> bool:
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS,
    )
    return hmac.compare_digest(derived.hex(), expected_hash)
