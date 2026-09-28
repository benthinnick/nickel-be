from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.api.dependencies import get_current_customer, get_seller_service
from app.core.config import get_settings
from app.core.constants import DEFAULT_PAGE_LIMIT, DEFAULT_PAGE_OFFSET, MAX_PAGE_LIMIT
from app.domain.models.customer import Customer
from app.domain.schemas.product import ProductResponse, product_to_response
from app.domain.schemas.seller import (
    AdjustStockRequest,
    CreateSellerProductRequest,
    CreateSellerRequest,
    InviteSellerMemberRequest,
    ProductCreateAcceptedResponse,
    SellerDetailResponse,
    SellerListResponse,
    SellerMembershipResponse,
    SellerProductListResponse,
    SellerResponse,
    membership_to_response,
    seller_detail_to_response,
    seller_list_to_response,
    seller_product_list_to_response,
    seller_to_response,
)
from app.infrastructure.kafka.handlers import route_event
from app.infrastructure.kafka.schemas.events import EventEnvelope
from app.services.seller_service import SellerService

router = APIRouter(prefix="/sellers", tags=["sellers"])


def _dispatch_locally(background_tasks: BackgroundTasks, event: EventEnvelope) -> None:
    if not get_settings().kafka_enabled:
        background_tasks.add_task(route_event, event)


@router.post("", response_model=SellerResponse, status_code=status.HTTP_201_CREATED)
async def create_seller(
    body: CreateSellerRequest,
    customer: Annotated[Customer, Depends(get_current_customer)],
    sellers: Annotated[SellerService, Depends(get_seller_service)],
) -> SellerResponse:
    seller = await sellers.create_seller(name=body.name, owner=customer)
    return seller_to_response(seller)


@router.get("/me", response_model=SellerListResponse)
async def list_my_sellers(
    customer: Annotated[Customer, Depends(get_current_customer)],
    sellers: Annotated[SellerService, Depends(get_seller_service)],
) -> SellerListResponse:
    items = await sellers.list_for_customer(customer.id)
    return seller_list_to_response(items)


@router.get("/{seller_id}", response_model=SellerDetailResponse)
async def get_seller(
    seller_id: UUID,
    customer: Annotated[Customer, Depends(get_current_customer)],
    sellers: Annotated[SellerService, Depends(get_seller_service)],
) -> SellerDetailResponse:
    seller = await sellers.get_for_member(seller_id, customer)
    memberships = await sellers.list_memberships(seller_id, customer)
    return seller_detail_to_response(seller, memberships)


@router.post(
    "/{seller_id}/members",
    response_model=SellerMembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member(
    seller_id: UUID,
    body: InviteSellerMemberRequest,
    customer: Annotated[Customer, Depends(get_current_customer)],
    sellers: Annotated[SellerService, Depends(get_seller_service)],
) -> SellerMembershipResponse:
    membership = await sellers.invite_member(seller_id, owner=customer, email=str(body.email))
    return membership_to_response(membership)


@router.delete("/{seller_id}/members/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    seller_id: UUID,
    customer_id: UUID,
    customer: Annotated[Customer, Depends(get_current_customer)],
    sellers: Annotated[SellerService, Depends(get_seller_service)],
) -> None:
    await sellers.remove_member(seller_id, owner=customer, customer_id=customer_id)


@router.get("/{seller_id}/products", response_model=SellerProductListResponse)
async def list_seller_products(
    seller_id: UUID,
    customer: Annotated[Customer, Depends(get_current_customer)],
    sellers: Annotated[SellerService, Depends(get_seller_service)],
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=DEFAULT_PAGE_OFFSET, ge=0),
) -> SellerProductListResponse:
    products, total = await sellers.list_products(seller_id, customer, limit=limit, offset=offset)
    return seller_product_list_to_response(products, total=total, limit=limit, offset=offset)


@router.post(
    "/{seller_id}/products",
    response_model=ProductCreateAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_seller_product(
    seller_id: UUID,
    body: CreateSellerProductRequest,
    background_tasks: BackgroundTasks,
    customer: Annotated[Customer, Depends(get_current_customer)],
    sellers: Annotated[SellerService, Depends(get_seller_service)],
) -> ProductCreateAcceptedResponse:
    accepted = await sellers.request_product_create(
        seller_id,
        customer,
        sku=body.sku,
        name=body.name,
        description=body.description,
        price=body.price,
        currency=body.currency,
        stock=body.stock,
        image_url=body.image_url,
    )
    _dispatch_locally(background_tasks, accepted.event)
    return ProductCreateAcceptedResponse(product_id=accepted.product_id, event_id=accepted.event_id)


@router.post("/{seller_id}/products/{product_id}/stock", response_model=ProductResponse)
async def adjust_stock(
    seller_id: UUID,
    product_id: UUID,
    body: AdjustStockRequest,
    customer: Annotated[Customer, Depends(get_current_customer)],
    sellers: Annotated[SellerService, Depends(get_seller_service)],
) -> ProductResponse:
    product = await sellers.adjust_stock(seller_id, product_id, customer, delta=body.delta)
    return product_to_response(product)


@router.post("/{seller_id}/products/{product_id}/hide", response_model=ProductResponse)
async def hide_product(
    seller_id: UUID,
    product_id: UUID,
    background_tasks: BackgroundTasks,
    customer: Annotated[Customer, Depends(get_current_customer)],
    sellers: Annotated[SellerService, Depends(get_seller_service)],
) -> ProductResponse:
    accepted = await sellers.hide_product(seller_id, product_id, customer)
    _dispatch_locally(background_tasks, accepted.event)
    return product_to_response(accepted.product)


@router.post("/{seller_id}/products/{product_id}/unhide", response_model=ProductResponse)
async def unhide_product(
    seller_id: UUID,
    product_id: UUID,
    background_tasks: BackgroundTasks,
    customer: Annotated[Customer, Depends(get_current_customer)],
    sellers: Annotated[SellerService, Depends(get_seller_service)],
) -> ProductResponse:
    accepted = await sellers.unhide_product(seller_id, product_id, customer)
    _dispatch_locally(background_tasks, accepted.event)
    return product_to_response(accepted.product)
