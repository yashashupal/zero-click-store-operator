from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Any


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    customer_name: str = "Walk-in Customer"


class ParsedItem(BaseModel):
    product: str
    quantity: int = Field(gt=0)


class ParsedOrder(BaseModel):
    items: List[ParsedItem]
    notes: str = ""


class OrderItemOut(BaseModel):
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float


class OrderOut(BaseModel):
    id: int
    customer_name: str
    original_request: str
    status: str
    total: float
    created_at: datetime
    items: List[OrderItemOut]


class ToolEvent(BaseModel):
    tool: str
    args: dict[str, Any] = {}
    result: dict[str, Any] = {}


class ChatResponse(BaseModel):
    ok: bool
    message: str
    parsed: ParsedOrder | None = None
    order: OrderOut | None = None
    warnings: List[str] = []
    tool_events: List[ToolEvent] = []