"""
Common schemas for pagination and API responses.
"""
from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel

T = TypeVar('T')

class PaginationParams(BaseModel):
    """Pagination parameters for requests."""
    page: Optional[int] = None
    page_size: Optional[int] = None

class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response with metadata."""
    data: List[T]
    total: int
    page: int
    page_size: int
    has_more: bool

