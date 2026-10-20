"""Account endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_db
from app.schemas.account import AccountRead
from app.utils.security import get_current_user

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _account_visible(account: dict, user: dict) -> bool:
    return user["role_name"] != "customer" or account["customer_id"] == user.get("customer_id")


@router.get("", response_model=list[AccountRead])
def list_accounts(connection=Depends(get_db), user=Depends(get_current_user)) -> list[AccountRead]:
    if user["role_name"] == "customer":
        rows = connection.execute(
            "SELECT * FROM account WHERE customer_id = %s ORDER BY account_id",
            (user.get("customer_id"),),
        ).fetchall()
    else:
        rows = connection.execute("SELECT * FROM account ORDER BY account_id").fetchall()
    return [AccountRead.model_validate(row) for row in rows]


@router.get("/{account_id}", response_model=AccountRead)
def get_account(account_id: int, connection=Depends(get_db), user=Depends(get_current_user)) -> AccountRead:
    row = connection.execute("SELECT * FROM account WHERE account_id = %s", (account_id,)).fetchone()
    if row is None or not _account_visible(row, user):
        raise HTTPException(status_code=404, detail="Account not found")
    return AccountRead.model_validate(row)
