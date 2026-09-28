from uuid import UUID


class AppError(Exception):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class NotFoundError(AppError):
    pass


class ConflictError(AppError):
    pass


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Not authenticated", *, code: str = "unauthorized") -> None:
        super().__init__(message, code=code)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden", *, code: str = "forbidden") -> None:
        super().__init__(message, code=code)


class ProductNotFoundError(NotFoundError):
    def __init__(self, product_id: UUID) -> None:
        super().__init__(
            f"Product {product_id} not found",
            code="product_not_found",
        )
        self.product_id = product_id


class SellerNotFoundError(NotFoundError):
    def __init__(self, seller_id: UUID) -> None:
        super().__init__(
            f"Seller {seller_id} not found",
            code="seller_not_found",
        )
        self.seller_id = seller_id


class CustomerNotFoundError(NotFoundError):
    def __init__(self, email: str) -> None:
        super().__init__(
            f"Customer {email} not found",
            code="customer_not_found",
        )
        self.email = email


class SkuAlreadyTakenError(ConflictError):
    def __init__(self, sku: str) -> None:
        super().__init__(
            f"SKU {sku} is already used by this seller",
            code="sku_already_taken",
        )
        self.sku = sku


class AlreadySellerMemberError(ConflictError):
    def __init__(self, customer_id: UUID) -> None:
        super().__init__(
            f"Customer {customer_id} is already a member of this seller",
            code="already_seller_member",
        )
        self.customer_id = customer_id


class CannotRemoveLastOwnerError(ConflictError):
    def __init__(self, seller_id: UUID) -> None:
        super().__init__(
            f"Seller {seller_id} must keep at least one owner",
            code="cannot_remove_last_owner",
        )
        self.seller_id = seller_id


class InsufficientStockError(AppError):
    def __init__(self, product_id: UUID, available: int) -> None:
        super().__init__(
            f"Product {product_id} has only {available} in stock",
            code="insufficient_stock",
        )
        self.product_id = product_id
        self.available = available


class InvalidProductError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_product")


class CartEmptyError(AppError):
    def __init__(self) -> None:
        super().__init__("Cart is empty", code="cart_empty")


class InvalidCartItemError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_cart_item")


class OrderNotFoundError(NotFoundError):
    def __init__(self, order_id: UUID) -> None:
        super().__init__(
            f"Order {order_id} not found",
            code="order_not_found",
        )
        self.order_id = order_id


class OrderNotPayableError(ConflictError):
    def __init__(self, order_id: UUID, status: str) -> None:
        super().__init__(
            f"Order {order_id} cannot be paid in status {status}",
            code="order_not_payable",
        )
        self.order_id = order_id
        self.status = status


class PaymentNotFoundError(NotFoundError):
    def __init__(self, payment_id: UUID) -> None:
        super().__init__(
            f"Payment {payment_id} not found",
            code="payment_not_found",
        )
        self.payment_id = payment_id


class DeliveryNotFoundError(NotFoundError):
    def __init__(self, *, order_id: UUID | None = None, delivery_id: UUID | None = None) -> None:
        identifier = delivery_id or order_id
        super().__init__(
            f"Delivery {identifier} not found",
            code="delivery_not_found",
        )
        self.order_id = order_id
        self.delivery_id = delivery_id
