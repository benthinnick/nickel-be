from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class SellerRole(StrEnum):
    OWNER = "owner"
    MEMBER = "member"


@dataclass(frozen=True)
class Seller:
    id: UUID
    name: str
    created_at: datetime


@dataclass(frozen=True)
class SellerMembership:
    seller_id: UUID
    customer_id: UUID
    role: SellerRole
    created_at: datetime
