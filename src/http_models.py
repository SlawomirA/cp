from typing import Optional, Any, TypeVar

from pydantic import BaseModel

T = TypeVar('T')
class DetailedResponse(BaseModel):
    code: int
    message: str
    data: Optional[T] = None
    error: Optional[str] = None