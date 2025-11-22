import pytest

from backend.app.core.security import create_access_token, decode_access_token


def test_create_and_decode_token_contains_sub_and_exp():
    token = create_access_token(user_id=123)
    assert isinstance(token, str) and token
    payload = decode_access_token(token)
    assert payload.get("sub") == "123"
    assert "exp" in payload


def test_expired_token_raises_value_error():
    expired_token = create_access_token(user_id=1, expires_minutes=-1)
    with pytest.raises(ValueError):
        decode_access_token(expired_token)


def test_invalid_token_raises_value_error():
    with pytest.raises(ValueError):
        decode_access_token("invalid.token.value")
