from pydantic import BaseModel
from typing import List, Optional

class FileKeywordResponse(BaseModel):
    FK_ID: int
    FI_ID: int
    Keyword: Optional[str]  # Use Optional if the field can be None

    class Config:
        orm_mode = True
        from_attributes = True


class LLMMessageResponse(BaseModel):
    LLM_ID: int
    Prompt: Optional[str]
    Answer: Optional[str]
    FI_ID: Optional[int]

    class Config:
        orm_mode = True
        from_attributes = True


class FileModelResponse(BaseModel):
    FI_ID: int
    Name: Optional[str]
    Content: Optional[str]
    Corretted_Content: Optional[str]
    Url: Optional[str]
    keywords: List[FileKeywordResponse] = []
    messages: List[LLMMessageResponse] = []  #

    class Config:
        orm_mode = True
        from_attributes = True

