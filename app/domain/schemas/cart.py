from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import MAX_CART_ITEM_QUANTITY
from app.domain.models.cart import Cart


class UpsertCartItemRequest(BaseModel):
    product_id: UUID
    quantity: int = Field(ge=1, le=MAX_CART_ITEM_QUANTITY)


class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    quantity: int


class CartResponse(BaseModel):
    items: list[CartItemResponse]


def cart_to_response(cart: Cart) -> CartResponse:
    return CartResponse(
        items=[
            CartItemResponse(product_id=item.product_id, quantity=item.quantity)
            for item in cart.items
        ],
    )
