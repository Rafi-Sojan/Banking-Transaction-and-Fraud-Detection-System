from decimal import Decimal

import pytest

from app.schemas.transaction import TransferRequest


def test_transfer_request_rejects_same_account() -> None:
    request = TransferRequest(
        source_account_id=1,
        destination_account_id=1,
        amount=Decimal("10.00"),
    )
    with pytest.raises(ValueError):
        request.ensure_distinct_accounts()


def test_transfer_request_normalizes_currency() -> None:
    request = TransferRequest(
        source_account_id=1,
        destination_account_id=2,
        amount=Decimal("10.00"),
        currency_code="usd",
    )
    assert request.currency_code == "USD"
