from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_customer
from app.domain.models.customer import Customer
from app.domain.schemas.customer import CustomerResponse, customer_to_response

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/me", response_model=CustomerResponse)
async def get_me(
    customer: Annotated[Customer, Depends(get_current_customer)],
) -> CustomerResponse:
    return customer_to_response(customer)
