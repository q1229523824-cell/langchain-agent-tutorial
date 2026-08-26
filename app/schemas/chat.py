from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "thread_id": "shopping-demo",
                    "message": "预算500元，推荐适合通勤的降噪耳机",
                },
                {"thread_id": "refund-demo", "message": "我要退款 order-1001"},
            ]
        },
    )

    thread_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    request_id: str
    thread_id: str
    intent: str
    route: str
    answer: str
    citations: list[str]
    business_result: dict[str, object]
    duration_ms: float


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


class ConversationSummary(BaseModel):
    thread_id: str
    message_count: int
    last_message: str
    updated_at: str


class ConversationListResponse(BaseModel):
    count: int
    conversations: list[ConversationSummary]


class ConversationHistoryResponse(BaseModel):
    thread_id: str
    count: int
    messages: list[MessageResponse]
