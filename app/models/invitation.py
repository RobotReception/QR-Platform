from pydantic import BaseModel, Field, model_validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class InvitationStatus(str, Enum):
    created = "created"
    sent = "sent"
    viewed = "viewed"
    accepted = "accepted"
    declined = "declined"
    checked_in = "checked_in"
    revoked = "revoked"
    expired = "expired"


class DeliveryChannel(str, Enum):
    sms = "sms"
    email = "email"
    whatsapp = "whatsapp"
    link = "link"
    print_ = "print"


class RsvpStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    maybe = "maybe"


class CheckinResult(str, Enum):
    success = "success"
    already_checked_in = "already_checked_in"
    revoked = "revoked"
    expired = "expired"
    invalid = "invalid"
    wrong_event = "wrong_event"
    wrong_gate = "wrong_gate"


# ── Invitations ──

class InvitationCreate(BaseModel):
    event_id: UUID
    template_id: Optional[UUID] = None
    guest_id: Optional[UUID] = None
    ticket_class: str = Field("normal", pattern="^(vip|normal)$")
    guest_name: Optional[str] = None
    guest_count: Optional[int] = Field(1, ge=1, le=10000)
    guest_name_ar: Optional[str] = None
    guest_phone: Optional[str] = None
    guest_whatsapp: Optional[str] = None
    guest_email: Optional[str] = None
    seat_number: Optional[str] = None
    table_number: Optional[str] = None
    gate_id: Optional[UUID] = None
    hall: Optional[str] = None
    zone: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None
    require_rsvp: Optional[bool] = False
    is_registration: Optional[bool] = False

    @model_validator(mode="after")
    def validate_rsvp_contact(self) -> 'InvitationCreate':
        if self.require_rsvp:
            phone = (self.guest_phone or "").strip()
            email = (self.guest_email or "").strip()
            if not phone and not email:
                raise ValueError("يجب توفير رقم الهاتف أو البريد الإلكتروني للضيف عند تفعيل تأكيد الحضور (RSVP)")
        return self


class QuickInviteCreate(BaseModel):
    event_id: UUID
    ticket_class: str = Field("normal", pattern="^(vip|normal)$")
    template_id: Optional[UUID] = None
    count: Optional[int] = Field(None, ge=1, le=10000)
    names: Optional[list[str]] = None
    gate_id: Optional[UUID] = None
    require_rsvp: Optional[bool] = False

    @model_validator(mode="after")
    def validate_rsvp_not_allowed(self) -> 'QuickInviteCreate':
        if self.require_rsvp:
            raise ValueError("لا يمكن تفعيل تأكيد الحضور (RSVP) عند التوليد السريع بالعدد أو الأسماء فقط (لعدم وجود بيانات الاتصال)")
        return self


class BulkInviteFromGuests(BaseModel):
    event_id: UUID
    guest_ids: list[UUID]
    ticket_class: str = Field("normal", pattern="^(vip|normal)$")
    template_id: Optional[UUID] = None
    gate_id: Optional[UUID] = None
    require_rsvp: Optional[bool] = False


class InvitationRead(BaseModel):
    id: UUID
    tenant_id: UUID
    event_id: UUID
    template_id: Optional[UUID] = None
    guest_id: Optional[UUID] = None
    ticket_class: str
    status: str
    token: str
    token_hash: Optional[str] = None
    qr_data: Optional[str] = None
    short_url: Optional[str] = None
    guest_name: Optional[str] = None
    guest_count: int = 1
    guest_name_ar: Optional[str] = None
    guest_phone: Optional[str] = None
    guest_whatsapp: Optional[str] = None
    guest_email: Optional[str] = None
    seat_number: Optional[str] = None
    table_number: Optional[str] = None
    gate_id: Optional[UUID] = None
    hall: Optional[str] = None
    zone: Optional[str] = None
    rsvp_status: Optional[str] = None
    rsvp_at: Optional[datetime] = None
    plus_one_count: int = 0
    rsvp_message: Optional[str] = None
    checked_in_at: Optional[datetime] = None
    checkin_count: int = 0
    barcode_svg_url: Optional[str] = None
    barcode_png_url: Optional[str] = None
    render_image_url: Optional[str] = None
    barcode_payload: Optional[str] = None
    barcode_signature: Optional[str] = None
    card_image_url: Optional[str] = None
    card_pdf_url: Optional[str] = None
    pdf_url: Optional[str] = None
    zip_url: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None
    is_registration: bool = False
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class InvitationUpdate(BaseModel):
    guest_name: Optional[str] = None
    guest_name_ar: Optional[str] = None
    guest_phone: Optional[str] = None
    guest_whatsapp: Optional[str] = None
    guest_email: Optional[str] = None
    seat_number: Optional[str] = None
    table_number: Optional[str] = None
    gate_id: Optional[UUID] = None
    hall: Optional[str] = None
    zone: Optional[str] = None
    ticket_class: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    rsvp_status: Optional[str] = None
    plus_one_count: Optional[int] = None
    rsvp_message: Optional[str] = None
    rsvp_at: Optional[datetime] = None
    guest_count: Optional[int] = None
    metadata: Optional[dict] = None
    is_registration: Optional[bool] = None



class InvitationSend(BaseModel):
    invitation_ids: list[UUID]
    channel: str = "link"
    message: Optional[str] = None


# ── Deliveries ──

class DeliveryRead(BaseModel):
    id: UUID
    invitation_id: UUID
    channel: str
    recipient: str
    status: str
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime


# ── Check-in ──

class CheckinRequest(BaseModel):
    token: str
    event_id: Optional[UUID] = None
    gate_id: Optional[UUID] = None
    scan_method: str = "qr"
    device_info: Optional[str] = None


class CheckinResponse(BaseModel):
    invitation_id: Optional[UUID] = None
    result: str
    guest_name: Optional[str] = None
    ticket_class: Optional[str] = None
    event_title: Optional[str] = None
    checkin_count: int = 0
    guest_count: int = 1
    message: str = ""


class CheckinRead(BaseModel):
    id: UUID
    invitation_id: UUID
    event_id: UUID
    gate_id: Optional[UUID] = None
    result: str
    scanned_by: Optional[UUID] = None
    scan_method: Optional[str] = None
    created_at: datetime


# ── RSVP ──

class RsvpRequest(BaseModel):
    status: str = "accepted"
    plus_one_count: int = Field(0, ge=0, le=10)
    message: Optional[str] = None
