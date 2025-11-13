"""
Standardized API response format.
All endpoints should return responses following this structure.
"""

from typing import Optional, TypeVar, Generic
from pydantic import BaseModel


T = TypeVar('T')


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    total: int = 0
    limit: int = 10
    page: int = 1
    total_pages: int = 1
    has_next: bool = False
    has_previous: bool = False


class StandardResponse(BaseModel, Generic[T]):
    """
    Standardized response format for all API endpoints.
    
    Example:
        {
            "success": true,
            "data": {...},
            "error": null,
            "message": "Operation successful",
            "meta": {
                "total": 1,
                "limit": 10,
                "page": 1,
                "total_pages": 1,
                "has_next": false,
                "has_previous": false
            }
        }
    """
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    message: str
    meta: PaginationMeta = PaginationMeta()
    
    class Config:
        json_schema_extra = {  # Changed from schema_extra
            "example": {
                "success": True,
                "data": {"id": "123", "status": "sent"},
                "error": None,
                "message": "Notification sent successfully",
                "meta": {
                    "total": 1,
                    "limit": 10,
                    "page": 1,
                    "total_pages": 1,
                    "has_next": False,
                    "has_previous": False
                }
            }
        }


def success_response(
    data: any,
    message: str = "Success",
    meta: Optional[PaginationMeta] = None
) -> StandardResponse:
    """Create a successful response"""
    return StandardResponse(
        success=True,
        data=data,
        error=None,
        message=message,
        meta=meta or PaginationMeta()
    )


def error_response(
    error: str,
    message: str = "An error occurred",
    data: any = None,
    meta: Optional[PaginationMeta] = None
) -> StandardResponse:
    """Create an error response"""
    return StandardResponse(
        success=False,
        data=data,
        error=error,
        message=message,
        meta=meta or PaginationMeta()
    )
