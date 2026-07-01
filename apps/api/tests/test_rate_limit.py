from app.services.rate_limit import check_rate_limit, reset_rate_limits


def test_rate_limiter_rejects_requests_after_window_limit() -> None:
    reset_rate_limits()

    assert check_rate_limit("api-key-hash", limit=2, window_seconds=60)
    assert check_rate_limit("api-key-hash", limit=2, window_seconds=60)
    assert not check_rate_limit("api-key-hash", limit=2, window_seconds=60)


def test_rate_limiter_keeps_identifiers_isolated() -> None:
    reset_rate_limits()

    assert check_rate_limit("first-key-hash", limit=1, window_seconds=60)
    assert not check_rate_limit("first-key-hash", limit=1, window_seconds=60)
    assert check_rate_limit("second-key-hash", limit=1, window_seconds=60)
