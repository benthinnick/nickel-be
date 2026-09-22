from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.tables import ProcessedEventRow


class ProcessedEventRepository(Protocol):
    async def exists(self, event_id: UUID) -> bool: ...

    async def record(self, event_id: UUID, event_type: str) -> None: ...


class SqlProcessedEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists(self, event_id: UUID) -> bool:
        row = await self._session.get(ProcessedEventRow, event_id)
        return row is not None

    async def record(self, event_id: UUID, event_type: str) -> None:
        self._session.add(
            ProcessedEventRow(
                event_id=event_id,
                event_type=event_type,
                processed_at=datetime.now(UTC),
            )
        )
        await self._session.flush()
