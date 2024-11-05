from typing import Optional, List

from pydantic import BaseModel

class SaveChatUpload(BaseModel):
    prompt: str
    answer: str
    fileId: Optional[int] = None
class SaveFileUpload(BaseModel):
    name: str
    url: str
    content: Optional[str] = None

class SaveKeywordsUpload(BaseModel):
    fileId: int
    keywords: List[str]