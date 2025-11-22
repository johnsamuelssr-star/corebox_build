import jwt
import pytest

from backend.app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hashing_not_plain():
    plain = "password123"
    hashed = get_password_hash(plain)
    assert hashed and hashed != plain


def test_verify_password():
    hashed = get_password_hash("secret")
    assert verify_password("secret", hashed)
    assert not verify_password("wrong", hashed)


def test_create_and_decode_access_token():
    payload = {"sub": "user123"}
    token = create_access_token(payload)
    assert isinstance(token, str) and token
    decoded = decode_access_token(token)
    assert decoded.get("sub") == "user123"


def test_access_token_expiration():
    token = create_access_token({"sub": "expired"}, expires_minutes=-1)
    with pytest.raises(ValueError):
        decode_access_token(token)

