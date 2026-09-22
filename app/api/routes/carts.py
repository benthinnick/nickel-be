from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_cart_owner, get_cart_service
from app.domain.models.cart import CartOwner
from app.domain.schemas.cart import CartResponse, UpsertCartItemRequest, cart_to_response
from app.domain.schemas.order import OrderResponse, order_to_response
from app.services.cart_service import CartService

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartResponse)
async def get_cart(
    owner: Annotated[CartOwner, Depends(get_cart_owner)],
    service: Annotated[CartService, Depends(get_cart_service)],
) -> CartResponse:
    cart = await service.get_cart(owner.key)
    return cart_to_response(cart)


@router.put("/items", response_model=CartResponse)
async def upsert_cart_item(
    body: UpsertCartItemRequest,
    owner: Annotated[CartOwner, Depends(get_cart_owner)],
    service: Annotated[CartService, Depends(get_cart_service)],
) -> CartResponse:
    cart = await service.upsert_item(
        owner.key,
        product_id=body.product_id,
        quantity=body.quantity,
    )
    return cart_to_response(cart)


@router.delete("/items/{product_id}", response_model=CartResponse)
async def remove_cart_item(
    product_id: UUID,
    owner: Annotated[CartOwner, Depends(get_cart_owner)],
    service: Annotated[CartService, Depends(get_cart_service)],
) -> CartResponse:
    cart = await service.remove_item(owner.key, product_id)
    return cart_to_response(cart)


@router.post("/checkout", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def checkout_cart(
    owner: Annotated[CartOwner, Depends(get_cart_owner)],
    service: Annotated[CartService, Depends(get_cart_service)],
) -> OrderResponse:
    order = await service.checkout(owner)
    return order_to_response(order)
