from pydantic import BaseModel


class QARequest(BaseModel):
    game_id: int
    question: str


class QAResponse(BaseModel):
    answer: str
    tools_used: list[str]
    game_name: str
