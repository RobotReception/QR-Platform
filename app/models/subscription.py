from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

__all__ = [
    "SubscriptionStatus",
    "SubscriptionRead",
    "SubscriptionWithPlan",
]


class SubscriptionStatus(str, Enum):
    trialing = "trialing"
    active = "active"
    past_due = "past_due"
    canceled = "canceled"
    unpaid = "unpaid"
    incomplete = "incomplete"


class SubscriptionRead(BaseModel):
    id: UUID
    tenant_id: UUID
    plan_id: UUID
    provider: str
    provider_customer_id: Optional[str] = None
    provider_subscription_id: Optional[str] = None
    status: SubscriptionStatus
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool
    trial_ends_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SubscriptionWithPlan(SubscriptionRead):
    plan_code: str
    plan_name: str
