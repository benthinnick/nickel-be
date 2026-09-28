import html
import re
from urllib.parse import urlparse

from app.core.exceptions import InvalidProductError

_TAG_RE = re.compile(r"<[^>]*>")
_WHITESPACE_RE = re.compile(r"\s+")


def sanitize_text(value: str) -> str:
    stripped = _TAG_RE.sub("", value)
    escaped = html.escape(html.unescape(stripped), quote=True)
    return _WHITESPACE_RE.sub(" ", escaped).strip()


def sanitize_image_url(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise InvalidProductError("image_url must be an http or https URL")
    return cleaned


def sanitize_product_fields(
    *,
    sku: str,
    name: str,
    description: str,
    image_url: str | None,
) -> tuple[str, str, str, str | None]:
    clean_sku = sanitize_text(sku)
    clean_name = sanitize_text(name)
    clean_description = sanitize_text(description)
    if not clean_sku:
        raise InvalidProductError("SKU is required")
    if not clean_name:
        raise InvalidProductError("Product name is required")
    return clean_sku, clean_name, clean_description, sanitize_image_url(image_url)
