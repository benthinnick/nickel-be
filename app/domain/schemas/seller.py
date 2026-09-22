from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.constants import DEFAULT_CURRENCY, DEFAULT_PAGE_LIMIT
from app.domain.models.product import Product
from app.domain.models.seller import Seller, SellerMembership, SellerRole
from app.domain.schemas.product import ProductResponse, product_to_response


class CreateSellerRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class InviteSellerMemberRequest(BaseModel):
    email: EmailStr


class CreateSellerProductRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=4000)
    price: Decimal = Field(gt=0)
    currency: str = Field(default=DEFAULT_CURRENCY, min_length=3, max_length=8)
    stock: int = Field(ge=0)
    image_url: str | None = Field(default=None, max_length=512)


class AdjustStockRequest(BaseModel):
    delta: int


class SellerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime


class SellerMembershipResponse(BaseModel):
    seller_id: UUID
    user_id: UUID
    role: SellerRole
    created_at: datetime


class SellerDetailResponse(SellerResponse):
    members: list[SellerMembershipResponse]


class SellerSummaryResponse(SellerResponse):
    role: SellerRole


class SellerListResponse(BaseModel):
    items: list[SellerSummaryResponse]


class ProductCreateAcceptedResponse(BaseModel):
    product_id: UUID
    event_id: UUID


class SellerProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    limit: int = DEFAULT_PAGE_LIMIT
    offset: int = 0


def seller_to_response(seller: Seller) -> SellerResponse:
    return SellerResponse(id=seller.id, name=seller.name, created_at=seller.created_at)


def membership_to_response(membership: SellerMembership) -> SellerMembershipResponse:
    return SellerMembershipResponse(
        seller_id=membership.seller_id,
        user_id=membership.user_id,
        role=membership.role,
        created_at=membership.created_at,
    )


def seller_detail_to_response(
    seller: Seller,
    memberships: list[SellerMembership],
) -> SellerDetailResponse:
    return SellerDetailResponse(
        id=seller.id,
        name=seller.name,
        created_at=seller.created_at,
        members=[membership_to_response(item) for item in memberships],
    )


def seller_list_to_response(items: list[tuple[Seller, SellerRole]]) -> SellerListResponse:
    return SellerListResponse(
        items=[
            SellerSummaryResponse(
                id=seller.id,
                name=seller.name,
                created_at=seller.created_at,
                role=role,
            )
            for seller, role in items
        ]
    )


def seller_product_list_to_response(
    products: list[Product],
    *,
    total: int,
    limit: int,
    offset: int,
) -> SellerProductListResponse:
    return SellerProductListResponse(
        items=[product_to_response(product) for product in products],
        total=total,
        limit=limit,
        offset=offset,
    )

