import pytest

from app.core.exceptions import InvalidProductError
from app.infrastructure.sanitization.html import (
    sanitize_image_url,
    sanitize_product_fields,
    sanitize_text,
)


def test_sanitize_text_strips_tags_and_escapes() -> None:
    cleaned = sanitize_text("<script>alert(1)</script>Coffee")

    assert "<" not in cleaned
    assert "script" not in cleaned.lower()
    assert "Coffee" in cleaned


def test_sanitize_product_fields_rejects_empty_name() -> None:
    with pytest.raises(InvalidProductError) as exc:
        sanitize_product_fields(
            sku="SKU-1",
            name="<script></script>",
            description="ok",
            image_url=None,
        )

    assert exc.value.code == "invalid_product"


def test_sanitize_image_url_rejects_javascript() -> None:
    with pytest.raises(InvalidProductError) as exc:
        sanitize_image_url("javascript:alert(1)")

    assert exc.value.code == "invalid_product"


def test_sanitize_image_url_accepts_https() -> None:
    assert sanitize_image_url("https://cdn.example.com/p.png") == "https://cdn.example.com/p.png"


def test_sanitize_text_is_idempotent_for_ampersands() -> None:
    once = sanitize_text("Coffee & Tea")
    twice = sanitize_text(once)

    assert once == "Coffee &amp; Tea"
    assert twice == once
