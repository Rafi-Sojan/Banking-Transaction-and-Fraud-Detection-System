from app.services import rate_limit_service


class _FakeConnection:
    def __init__(self, row):
        self.row = row

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, _query, _params):
        return self

    def fetchone(self):
        return self.row


def test_shared_rate_limit_allows_requests_within_limit(monkeypatch):
    monkeypatch.setattr(
        rate_limit_service,
        "get_connection",
        lambda: _FakeConnection({"request_count": 2, "retry_after": 45}),
    )

    result = rate_limit_service.check_rate_limit("127.0.0.1:/api/v1/auth/login", 3, 60)

    assert result.allowed is True
    assert result.retry_after == 45


def test_shared_rate_limit_rejects_requests_over_limit(monkeypatch):
    monkeypatch.setattr(
        rate_limit_service,
        "get_connection",
        lambda: _FakeConnection({"request_count": 4, "retry_after": 32}),
    )

    result = rate_limit_service.check_rate_limit("127.0.0.1:/api/v1/auth/login", 3, 60)

    assert result.allowed is False
    assert result.retry_after == 32
