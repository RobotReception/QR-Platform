from pydantic import BaseModel, Field
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime
from app.models.event import TicketClass

class RegistrationFormField(BaseModel):
    id: str = Field(..., description="Unique key for the field (e.g. company, job_title)")
    type: str = Field(..., description="Field type: text, number, email, phone, select, date, checkbox")
    label: str = Field(..., description="Field label in Arabic")
    label_en: Optional[str] = Field(None, description="Field label in English")
    required: bool = False
    system: bool = False  # True for built-in fields like guest_name, guest_phone, guest_email
    options: Optional[List[str]] = None  # Options for dropdown/select type

class RegistrationFormRead(BaseModel):
    id: UUID
    tenant_id: UUID
    event_id: UUID
    is_enabled: bool
    barcode_generation_mode: str
    default_ticket_class: TicketClass
    default_template_id: Optional[UUID] = None
    success_message_ar: Optional[str] = None
    success_message_en: Optional[str] = None
    pending_approval_message_ar: Optional[str] = None
    pending_approval_message_en: Optional[str] = None
    fields: List[RegistrationFormField] = []
    created_at: datetime
    updated_at: datetime

class RegistrationFormCreate(BaseModel):
    is_enabled: bool = False
    barcode_generation_mode: str = "immediate"
    default_ticket_class: TicketClass = TicketClass.normal
    default_template_id: Optional[UUID] = None
    success_message_ar: Optional[str] = None
    success_message_en: Optional[str] = None
    pending_approval_message_ar: Optional[str] = None
    pending_approval_message_en: Optional[str] = None
    fields: List[RegistrationFormField] = []

class RegistrationFormUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    barcode_generation_mode: Optional[str] = None
    default_ticket_class: Optional[TicketClass] = None
    default_template_id: Optional[UUID] = None
    success_message_ar: Optional[str] = None
    success_message_en: Optional[str] = None
    pending_approval_message_ar: Optional[str] = None
    pending_approval_message_en: Optional[str] = None
    fields: Optional[List[RegistrationFormField]] = None

class PublicRegistrationSubmit(BaseModel):
    guest_name: str = Field(..., min_length=1)
    guest_phone: str = Field(..., min_length=5)
    guest_email: Optional[str] = None
    custom_answers: Optional[dict[str, Any]] = None
