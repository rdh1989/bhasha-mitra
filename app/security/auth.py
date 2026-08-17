from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path


ROLES = ("admin", "operator", "user")
SESSION_TIMEOUT = timedelta(minutes=15)
PASSWORD_ITERATIONS = 600_000


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: int
    username: str
    role: str


class SQLiteAuthRepository:
    def __init__(self, database_directory: Path) -> None:
        self._database_path = Path(database_directory) / "bhasha_mitra.db"
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self._database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _hash_password(password: str, salt: bytes | None = None) -> str:
        password_salt = salt or secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            password_salt,
            PASSWORD_ITERATIONS,
        )
        return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${password_salt.hex()}${digest.hex()}"

    @classmethod
    def _verify_password(cls, password: str, encoded: str) -> bool:
        try:
            algorithm, iterations, salt, expected = encoded.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            digest = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt),
                int(iterations),
            )
            return hmac.compare_digest(digest.hex(), expected)
        except (TypeError, ValueError):
            return False

    def _initialize_database(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('admin', 'operator', 'user')),
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    last_seen_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id
                ON user_sessions(user_id);
                """
            )
            admin_exists = connection.execute(
                "SELECT 1 FROM users WHERE username = 'admin'"
            ).fetchone()
            if admin_exists is None:
                connection.execute(
                    """
                    INSERT INTO users
                        (username, password_hash, role, is_active, created_at)
                    VALUES (?, ?, 'admin', 1, ?)
                    """,
                    (
                        "admin",
                        self._hash_password("admin"),
                        datetime.now(UTC).isoformat(),
                    ),
                )

    def authenticate(self, username: str, password: str) -> AuthenticatedUser | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, username, password_hash, role
                FROM users
                WHERE username = ? AND is_active = 1
                """,
                (username.strip(),),
            ).fetchone()
        if row is None or not self._verify_password(password, row["password_hash"]):
            return None
        return AuthenticatedUser(row["id"], row["username"], row["role"])

    def create_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = datetime.now(UTC)
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM user_sessions WHERE expires_at <= ?",
                (now.isoformat(),),
            )
            connection.execute(
                """
                INSERT INTO user_sessions (token_hash, user_id, last_seen_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (token_hash, user_id, now.isoformat(), (now + SESSION_TIMEOUT).isoformat()),
            )
        return token

    def get_session_user(
        self,
        token: str,
        refresh: bool = False,
    ) -> AuthenticatedUser | None:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = datetime.now(UTC)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT users.id, users.username, users.role, user_sessions.expires_at
                FROM user_sessions
                JOIN users ON users.id = user_sessions.user_id
                WHERE user_sessions.token_hash = ? AND users.is_active = 1
                """,
                (token_hash,),
            ).fetchone()
            if row is None or datetime.fromisoformat(row["expires_at"]) <= now:
                connection.execute(
                    "DELETE FROM user_sessions WHERE token_hash = ?",
                    (token_hash,),
                )
                return None
            if refresh:
                connection.execute(
                    """
                    UPDATE user_sessions SET last_seen_at = ?, expires_at = ?
                    WHERE token_hash = ?
                    """,
                    (now.isoformat(), (now + SESSION_TIMEOUT).isoformat(), token_hash),
                )
        return AuthenticatedUser(row["id"], row["username"], row["role"])

    def delete_session(self, token: str) -> None:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM user_sessions WHERE token_hash = ?",
                (token_hash,),
            )

    def list_users(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, username, role, is_active, created_at
                FROM users ORDER BY username COLLATE NOCASE
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def create_user(self, username: str, password: str, role: str) -> None:
        if role not in ROLES:
            raise ValueError("Invalid role.")
        if not username.strip() or not password:
            raise ValueError("Username and password are required.")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO users (username, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (
                    username.strip(),
                    self._hash_password(password),
                    role,
                    datetime.now(UTC).isoformat(),
                ),
            )

    def update_role(self, user_id: int, role: str) -> None:
        if role not in ROLES:
            raise ValueError("Invalid role.")
        with self._connect() as connection:
            current = connection.execute(
                "SELECT role FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if current is None:
                raise ValueError("User not found.")
            if current["role"] == role:
                return
            if current["role"] == "admin" and role != "admin":
                admin_count = connection.execute(
                    "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1"
                ).fetchone()[0]
                if admin_count <= 1:
                    raise ValueError("The final administrator cannot be demoted.")
            cursor = connection.execute(
                "UPDATE users SET role = ? WHERE id = ?",
                (role, user_id),
            )
            connection.execute(
                "DELETE FROM user_sessions WHERE user_id = ?",
                (user_id,),
            )