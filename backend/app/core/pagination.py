from typing import Generic, Sequence, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pydantic model representing pagination query parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    size: int = Field(default=20, ge=1, le=100, description="Page size limit")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class Paginated(BaseModel, Generic[T]):
    """Standard generic wrapper representing a paginated data response."""

    items: Sequence[T]
    total: int
    page: int
    size: int
    pages: int


def paginate_list(items: Sequence[T], params: PaginationParams, total: int) -> Paginated[T]:
    """Helper to construct a Paginated DTO structure from raw items."""
    import math

    pages = math.ceil(total / params.size) if total > 0 else 0
    return Paginated(items=items, total=total, page=params.page, size=params.size, pages=pages)
