from app.repositories.customer_repository import SqlCustomerRepository
from app.services.customer_service import CustomerService


def _customers(db_session) -> CustomerService:
    return CustomerService(SqlCustomerRepository(db_session))


async def test_ensure_from_identity_is_idempotent(db_session) -> None:
    customers = _customers(db_session)

    first = await customers.ensure_from_identity(subject="kc-1", email="Ada@Example.com")
    second = await customers.ensure_from_identity(subject="kc-1", email="ada@example.com")

    assert first.email == "ada@example.com"
    assert second.id == first.id


async def test_ensure_from_identity_updates_cached_email(db_session) -> None:
    customers = _customers(db_session)
    await customers.ensure_from_identity(subject="kc-1", email="old@example.com")

    updated = await customers.ensure_from_identity(subject="kc-1", email="new@example.com")
    loaded = await customers.get_by_email("new@example.com")

    assert updated.email == "new@example.com"
    assert loaded is not None
    assert loaded.id == updated.id
