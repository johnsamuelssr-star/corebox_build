from datetime import UTC

from backend.app.core.time import utc_now


def test_utc_now_is_timezone_aware_utc():
    value = utc_now()
    assert value.tzinfo is UTC
