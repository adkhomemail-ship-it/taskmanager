from jose import jwt
from pydantic import ValidationError
from fastapi import HTTPException

from app.auth import authenticate_user, create_access_token, get_current_user, get_password_hash, verify_password
from app.config import settings
from app.models import User
from app.schemas import UserCreate


def test_user_create_accepts_ascii_alnum_username():
    data = UserCreate(username="User123", password="password123")
    assert data.username == "User123"


def test_user_create_rejects_non_ascii_or_punctuated_username():
    for username in ["иван", "user-name", "user name", "user_1"]:
        try:
            UserCreate(username=username, password="password123")
        except ValidationError as exc:
            assert "Логин должен содержать" in str(exc)
        else:
            raise AssertionError(f"username {username!r} should be invalid")


def test_password_hash_round_trip_and_negative_case():
    hashed = get_password_hash("password123")
    assert hashed != "password123"
    assert verify_password("password123", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_create_access_token_contains_subject_and_expiration():
    token = create_access_token({"sub": "alice"})
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert payload["sub"] == "alice"
    assert "exp" in payload


def test_authenticate_user_success_and_failures(db_session):
    user = User(username="alice", hashed_password=get_password_hash("password123"))
    db_session.add(user)
    db_session.commit()

    assert authenticate_user(db_session, "alice", "password123").username == "alice"
    assert authenticate_user(db_session, "alice", "bad-password") is None
    assert authenticate_user(db_session, "missing", "password123") is None


def test_get_current_user_returns_user_for_valid_token(db_session):
    user = User(username="alice", hashed_password=get_password_hash("password123"))
    db_session.add(user)
    db_session.commit()

    token = create_access_token({"sub": "alice"})
    assert get_current_user(token=token, db=db_session).username == "alice"


def test_get_current_user_rejects_invalid_missing_and_unknown_tokens(db_session):
    bad_tokens = [
        "not-a-jwt",
        create_access_token({"other": "missing-sub"}),
        create_access_token({"sub": "ghost"}),
    ]
    for token in bad_tokens:
        try:
            get_current_user(token=token, db=db_session)
        except HTTPException as exc:
            assert exc.status_code == 401
            assert exc.headers["WWW-Authenticate"] == "Bearer"
        else:
            raise AssertionError("invalid token should raise HTTPException")
