from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Customer:
    id: UUID
    keycloak_sub: str
    email: str
    created_at: datetime
