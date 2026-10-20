"""Customer endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_db
from app.schemas.customer import CustomerRead
from app.utils.security import get_current_user

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerRead])
def list_customers(connection=Depends(get_db), user=Depends(get_current_user)) -> list[CustomerRead]:
    if user["role_name"] == "customer":
        rows = connection.execute("SELECT * FROM customer WHERE customer_id = %s", (user.get("customer_id"),)).fetchall()
    else:
        rows = connection.execute("SELECT * FROM customer ORDER BY customer_id").fetchall()
    return [CustomerRead.model_validate(row) for row in rows]


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, connection=Depends(get_db), user=Depends(get_current_user)) -> CustomerRead:
    if user["role_name"] == "customer" and user.get("customer_id") != customer_id:
        raise HTTPException(status_code=404, detail="Customer not found")
    row = connection.execute("SELECT * FROM customer WHERE customer_id = %s", (customer_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return CustomerRead.model_validate(row)
