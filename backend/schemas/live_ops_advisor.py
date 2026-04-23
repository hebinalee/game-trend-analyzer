from pydantic import BaseModel


class LiveOpsAdvisorRequest(BaseModel):
    game_id: int
    question: str


class LiveOpsAdvisorResponse(BaseModel):
    answer: str
    tools_used: list[str]
    game_name: str
