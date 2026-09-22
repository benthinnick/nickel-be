from dataclasses import replace
from decimal import Decimal
from uuid import UUID

from app.core.constants import DEFAULT_CURRENCY, MAX_CART_ITEM_QUANTITY
from app.core.exceptions import (
    CartEmptyError,
    InsufficientStockError,
    InvalidCartItemError,
    ProductNotFoundError,
)
from app.domain.models.cart import Cart, CartItem, CartOwner, session_cart_key, user_cart_key
from app.domain.models.order import Order, OrderItem
from app.domain.models.product import Product, ProductStatus
from app.repositories.cart_repository import CartRepository
from app.repositories.product_repository import ProductRepository
from app.services.order_service import OrderService


class CartService:
    def __init__(
        self,
        cart_repository: CartRepository,
        product_repository: ProductRepository,
        order_service: OrderService,
    ) -> None:
        self._carts = cart_repository
        self._products = product_repository
        self._orders = order_service

    async def get_cart(self, owner_key: str) -> Cart:
        cart = await self._carts.get(owner_key)
        if cart is None:
            return Cart(owner_key=owner_key, items=())
        return cart

    async def upsert_item(self, owner_key: str, *, product_id: UUID, quantity: int) -> Cart:
        if quantity < 1 or quantity > MAX_CART_ITEM_QUANTITY:
            raise InvalidCartItemError(
                f"Quantity must be between 1 and {MAX_CART_ITEM_QUANTITY}",
            )
        product = await self._products.get_by_id(product_id)
        if product is None or product.status != ProductStatus.ACTIVE:
            raise ProductNotFoundError(product_id)
        if quantity > product.stock:
            raise InsufficientStockError(product_id, product.stock)

        cart = await self.get_cart(owner_key)
        items = {item.product_id: item for item in cart.items}
        items[product_id] = CartItem(product_id=product_id, quantity=quantity)
        updated = replace(cart, items=tuple(items.values()))
        await self._carts.save(updated)
        return updated

    async def remove_item(self, owner_key: str, product_id: UUID) -> Cart:
        cart = await self.get_cart(owner_key)
        updated = replace(
            cart,
            items=tuple(item for item in cart.items if item.product_id != product_id),
        )
        if updated.items:
            await self._carts.save(updated)
        else:
            await self._carts.pop(owner_key)
        return updated

    async def checkout(self, owner: CartOwner) -> Order:
        cart = await self._carts.pop(owner.key)
        if cart is None or not cart.items:
            raise CartEmptyError()

        try:
            return await self._create_order(owner, cart)
        except Exception:
            await self._carts.save(cart)
            raise

    async def merge_session_into_user(self, *, session_id: str, user_id: UUID) -> Cart:
        session_key = session_cart_key(session_id)
        user_key = user_cart_key(user_id)
        session_cart = await self._carts.pop(session_key)
        user_cart = await self.get_cart(user_key)
        if session_cart is None or not session_cart.items:
            return user_cart
        merged_items = {item.product_id: item for item in user_cart.items}
        for item in session_cart.items:
            existing = merged_items.get(item.product_id)
            quantity = item.quantity + (existing.quantity if existing else 0)
            merged_items[item.product_id] = CartItem(
                product_id=item.product_id,
                quantity=min(quantity, MAX_CART_ITEM_QUANTITY),
            )
        merged = Cart(owner_key=user_key, items=tuple(merged_items.values()))
        await self._carts.save(merged)
        return merged

    async def _create_order(self, owner: CartOwner, cart: Cart) -> Order:
        order_items: list[OrderItem] = []
        total = Decimal("0")
        originals: list[Product] = []
        for item in cart.items:
            product = await self._products.get_by_id(item.product_id)
            if product is None or product.status != ProductStatus.ACTIVE:
                raise ProductNotFoundError(item.product_id)
            if item.quantity > product.stock:
                raise InsufficientStockError(item.product_id, product.stock)
            originals.append(product)
            await self._products.save(replace(product, stock=product.stock - item.quantity))
            line_total = product.price * item.quantity
            total += line_total
            order_items.append(
                OrderItem(
                    product_id=product.id,
                    sku=product.sku,
                    name=product.name,
                    unit_price=product.price,
                    quantity=item.quantity,
                    line_total=line_total,
                )
            )
        try:
            return await self._orders.create_from_checkout(
                session_id=owner.session_id,
                user_id=owner.user_id,
                items=tuple(order_items),
                currency=DEFAULT_CURRENCY,
                total=total,
            )
        except Exception:
            for product in originals:
                await self._products.save(product)
            raise
