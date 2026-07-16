from pydantic import BaseModel
from typing import Optional, List


class SessionCreate(BaseModel):
    title: Optional[str] = "New Research Session"


class SessionOut(BaseModel):
    id: str
    title: str
    created_at: str


class ChatRequest(BaseModel):
    message: str
    use_web_search: bool = True
    use_documents: bool = True


class ChatStep(BaseModel):
    type: str          # "tool_call" | "tool_result" | "final"
    tool: Optional[str] = None
    detail: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    steps: List[ChatStep] = []


class NoteCreate(BaseModel):
    title: str
    content: str


class NoteOut(BaseModel):
    id: int
    title: str
    content: str
    created_at: str


class MessageOut(BaseModel):
    role: str
    content: str
    created_at: str
