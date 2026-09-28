from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.models.customer import Customer


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    created_at: datetime


def customer_to_response(customer: Customer) -> CustomerResponse:
    return CustomerResponse(id=customer.id, email=customer.email, created_at=customer.created_at)
