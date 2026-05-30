from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

__all__ = [
    "UsagePeriod",
    "PlanRead",
    "PlanLimitRead",
    "PlanWithLimits",
]


class UsagePeriod(str, Enum):
    month = "month"
    day = "day"
    none = "none"


class PlanRead(BaseModel):
    id: UUID
    code: str
    name: str
    price_monthly: float
    price_yearly: Optional[float] = None
    currency: str
    is_active: bool
    sort_order: int


class PlanLimitRead(BaseModel):
    id: UUID
    plan_id: UUID
    key: str
    value: int
    period: UsagePeriod


class PlanWithLimits(PlanRead):
    limits: list[PlanLimitRead] = []
