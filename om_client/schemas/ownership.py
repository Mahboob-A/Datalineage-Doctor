from typing import Literal

from pydantic import BaseModel


class EntityOwner(BaseModel):
    """Normalized owner entry for supported OpenMetadata entities."""

    name: str
    email: str
    type: Literal["user", "team"]
