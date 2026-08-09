from pathlib import Path

from infrastructure.security import UserRepository


def test_user_authentication(tmp_path: Path):
    repository = UserRepository(tmp_path / "users.db")
    repository.initialize()

    user = repository.authenticate("admin", "admin123")
    assert user is not None
    assert user.username == "admin"
    assert user.role == "admin"

    assert repository.authenticate("admin", "wrong-password") is None


def test_default_user_and_owner_accounts(tmp_path: Path):
    repository = UserRepository(tmp_path / "users.db")
    repository.initialize()

    user = repository.authenticate("user", "user123")
    assert user is not None
    assert user.role == "user"

    owner = repository.authenticate("owner", "owner123")
    assert owner is not None
    assert owner.role == "owner"
