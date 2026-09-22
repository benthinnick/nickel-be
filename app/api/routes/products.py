from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_product_service
from app.core.constants import DEFAULT_PAGE_LIMIT, DEFAULT_PAGE_OFFSET, MAX_PAGE_LIMIT
from app.domain.schemas.product import (
    ProductListResponse,
    ProductResponse,
    product_list_to_response,
    product_to_response,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductListResponse)
async def list_products(
    service: Annotated[ProductService, Depends(get_product_service)],
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=DEFAULT_PAGE_OFFSET, ge=0),
) -> ProductListResponse:
    products, total = await service.list_products(limit=limit, offset=offset)
    return product_list_to_response(products, total=total, limit=limit, offset=offset)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductResponse:
    product = await service.get_product(product_id)
    return product_to_response(product)
