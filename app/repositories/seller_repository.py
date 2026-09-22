from datetime import UTC
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.seller import Seller, SellerMembership, SellerRole
from app.infrastructure.database.tables import SellerMembershipRow, SellerRow


class SellerRepository(Protocol):
    async def add(self, seller: Seller) -> None: ...

    async def get_by_id(self, seller_id: UUID) -> Seller | None: ...

    async def list_for_user(self, user_id: UUID) -> list[tuple[Seller, SellerRole]]: ...

    async def add_membership(self, membership: SellerMembership) -> None: ...

    async def remove_membership(self, seller_id: UUID, user_id: UUID) -> None: ...

    async def get_membership(self, seller_id: UUID, user_id: UUID) -> SellerMembership | None: ...

    async def list_memberships(self, seller_id: UUID) -> list[SellerMembership]: ...

    async def count_owners(self, seller_id: UUID) -> int: ...


class SqlSellerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, seller: Seller) -> None:
        self._session.add(
            SellerRow(id=seller.id, name=seller.name, created_at=seller.created_at)
        )
        await self._session.flush()

    async def get_by_id(self, seller_id: UUID) -> Seller | None:
        row = await self._session.get(SellerRow, seller_id)
        return _to_seller(row) if row is not None else None

    async def list_for_user(self, user_id: UUID) -> list[tuple[Seller, SellerRole]]:
        result = await self._session.execute(
            select(SellerRow, SellerMembershipRow.role)
            .join(SellerMembershipRow, SellerMembershipRow.seller_id == SellerRow.id)
            .where(SellerMembershipRow.user_id == user_id)
            .order_by(SellerRow.name)
        )
        return [(_to_seller(seller), SellerRole(role)) for seller, role in result.all()]

    async def add_membership(self, membership: SellerMembership) -> None:
        self._session.add(
            SellerMembershipRow(
                seller_id=membership.seller_id,
                user_id=membership.user_id,
                role=membership.role.value,
                created_at=membership.created_at,
            )
        )
        await self._session.flush()

    async def remove_membership(self, seller_id: UUID, user_id: UUID) -> None:
        row = await self._session.get(SellerMembershipRow, (seller_id, user_id))
        if row is None:
            return
        await self._session.delete(row)
        await self._session.flush()

    async def get_membership(self, seller_id: UUID, user_id: UUID) -> SellerMembership | None:
        row = await self._session.get(SellerMembershipRow, (seller_id, user_id))
        return _to_membership(row) if row is not None else None

    async def list_memberships(self, seller_id: UUID) -> list[SellerMembership]:
        result = await self._session.scalars(
            select(SellerMembershipRow)
            .where(SellerMembershipRow.seller_id == seller_id)
            .order_by(SellerMembershipRow.created_at)
        )
        return [_to_membership(row) for row in result.all()]

    async def count_owners(self, seller_id: UUID) -> int:
        total = await self._session.scalar(
            select(func.count())
            .select_from(SellerMembershipRow)
            .where(
                SellerMembershipRow.seller_id == seller_id,
                SellerMembershipRow.role == SellerRole.OWNER.value,
            )
        )
        return int(total or 0)


def _to_seller(row: SellerRow) -> Seller:
    created_at = row.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return Seller(id=row.id, name=row.name, created_at=created_at)


def _to_membership(row: SellerMembershipRow) -> SellerMembership:
    created_at = row.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return SellerMembership(
        seller_id=row.seller_id,
        user_id=row.user_id,
        role=SellerRole(row.role),
        created_at=created_at,
    )
