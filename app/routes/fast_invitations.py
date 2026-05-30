"""
Fast Invitations API - Integrated Generation Endpoints.
Provides ultra-fast invitation creation with barcode, PDF, and ZIP generation.

Features:
- Single API call for everything
- Parallel processing for maximum speed
- Real-time progress tracking
- Multiple input formats
- Professional PDF output
- Optimized for large batches
"""
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional, Dict, Any
import logging
from urllib.parse import unquote, urlparse

from app.auth import get_current_user, get_tenant_id_from_header, CurrentUser
from app.database import get_db
from app.services.permission_service import require_permission
from app.services.audit_service import log_audit
from app.services.fast_generation_service import generate_invitations_fast, FastGenerationResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fast-invitations", tags=["Fast Invitations"])


# ══════════════════════════════════════════════
# Pydantic Models
# ══════════════════════════════════════════════

from pydantic import BaseModel, Field
from app.models.invitation import InvitationRead

class FastInvitationRequest(BaseModel):
    """Request model for fast invitation generation."""
    event_id: UUID = Field(..., description="Event ID")
    invitations: List[Dict[str, Any]] = Field(
        ..., 
        min_items=1,
        max_items=1000,
        description="List of invitation data (max 1000 per request)"
    )
    layout_config: Optional[Dict[str, Any]] = Field(
        None,
        description="PDF layout configuration"
    )
    generate_zip: bool = Field(True, description="Generate ZIP file")
    generate_pdf: bool = Field(True, description="Generate PDF file")
    upload_individual_barcodes: bool = Field(
        True,
        description="Upload a separate PNG for every invitation. Disable for faster PDF/ZIP print batches."
    )


class FastInvitationByCount(BaseModel):
    """Request model for creating invitations by count."""
    event_id: UUID = Field(..., description="Event ID")
    count: int = Field(..., ge=1, le=1000, description="Number of invitations")
    ticket_class: str = Field("normal", pattern="^(vip|normal)$", description="Ticket class")
    guest_name_prefix: Optional[str] = Field(None, description="Guest name prefix")
    layout_config: Optional[Dict[str, Any]] = Field(None, description="PDF layout configuration")
    generate_zip: bool = Field(True, description="Generate ZIP file")
    generate_pdf: bool = Field(True, description="Generate PDF file")
    upload_individual_barcodes: bool = Field(
        True,
        description="Upload a separate PNG for every invitation. Disable for faster PDF/ZIP print batches."
    )


class FastGenerationResponse(BaseModel):
    """Response model for fast generation."""
    success: bool
    total_invitations: int
    generation_time_ms: int
    pdf_url: Optional[str] = None
    zip_url: Optional[str] = None
    pdf_size_mb: Optional[float] = None
    zip_size_mb: Optional[float] = None
    error_message: Optional[str] = None


class GenerationProgressResponse(BaseModel):
    """Response model for generation progress."""
    status: str
    progress_percent: int
    total_invitations: int
    processed_invitations: int
    current_stage: str
    estimated_remaining_seconds: Optional[int] = None


class GenerationHistoryItem(BaseModel):
    """A completed barcode generation operation for an event."""
    id: str
    total_invitations: int
    vip_count: int
    normal_count: int
    generated_at: Optional[str] = None
    pdf_url: Optional[str] = None
    zip_url: Optional[str] = None


class DeleteGenerationResponse(BaseModel):
    success: bool
    deleted_invitations: int
    deleted_files: int


def _storage_path_from_signed_url(url: Optional[str]) -> Optional[str]:
    """Extract Supabase Storage object path from a signed/public URL."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        path = unquote(parsed.path)
        marker = "/object/sign/invitations/"
        if marker not in path:
            marker = "/object/public/invitations/"
        if marker not in path:
            return None
        return path.split(marker, 1)[1]
    except Exception:
        return None


# ══════════════════════════════════════════════
# FAST GENERATION ENDPOINTS
# ══════════════════════════════════════════════

@router.post("/generate", response_model=FastGenerationResponse, status_code=201)
async def generate_invitations_fast_endpoint(
    request: FastInvitationRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate invitations with barcodes, PDF, and ZIP in one fast operation.
    
    This endpoint creates invitations, generates barcodes, creates PDF and ZIP files,
    and returns download URLs - all in a single optimized process.
    
    Performance: ~1000 invitations in 30-60 seconds
    """
    tenant_id = get_tenant_id_from_header(http_request)
    await require_permission(db, tenant_id, user.id, "invitations.create")
    
    # Validate event exists and belongs to tenant
    event_check = await db.execute(
        text("SELECT id FROM events WHERE id = :eid AND tenant_id = :tid"),
        {"eid": str(request.event_id), "tid": str(tenant_id)}
    )
    if not event_check.first():
        raise HTTPException(404, "الحدث غير موجود")
    
    # Check quota
    await _check_event_quota(db, str(tenant_id), str(request.event_id), request.invitations)
    
    try:
        # Execute fast generation
        result = await generate_invitations_fast(
            db=db,
            tenant_id=str(tenant_id),
            event_id=str(request.event_id),
            invitations_data=request.invitations,
            layout_config=request.layout_config,
            generate_pdf=request.generate_pdf,
            generate_zip=request.generate_zip,
            upload_individual_barcodes=request.upload_individual_barcodes,
        )
        # Log the operation
        await log_audit(
            db, tenant_id=tenant_id, actor_user_id=user.id,
            action="fast_invitations.generate", resource_type="event", 
            resource_id=str(request.event_id),
            metadata={
                "total_invitations": result.total_invitations,
                "generation_time_ms": result.generation_time_ms,
                "pdf_size_mb": result.pdf_size / (1024*1024) if result.pdf_size else None,
                "zip_size_mb": result.zip_size / (1024*1024) if result.zip_size else None
            }
        )
        await db.commit()
        
        # Prepare response
        response = FastGenerationResponse(
            success=result.success,
            total_invitations=result.total_invitations,
            generation_time_ms=result.generation_time_ms,
            pdf_url=result.pdf_url,
            zip_url=result.zip_url,
            pdf_size_mb=result.pdf_size / (1024*1024) if result.pdf_size else None,
            zip_size_mb=result.zip_size / (1024*1024) if result.zip_size else None,
            error_message=result.error_message
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Fast generation failed: {e}")
        raise HTTPException(500, f"فشل في التوليد السريع: {str(e)}")


@router.post("/generate-by-count", response_model=FastGenerationResponse, status_code=201)
async def generate_invitations_by_count(
    request: FastInvitationByCount,
    http_request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate invitations by count with automatic naming.
    
    Creates the specified number of invitations with sequential guest names
    (Guest 1, Guest 2, etc.) or with custom prefix.
    """
    tenant_id = get_tenant_id_from_header(http_request)
    await require_permission(db, tenant_id, user.id, "invitations.create")
    
    # Validate event exists
    event_check = await db.execute(
        text("SELECT id FROM events WHERE id = :eid AND tenant_id = :tid"),
        {"eid": str(request.event_id), "tid": str(tenant_id)}
    )
    if not event_check.first():
        raise HTTPException(404, "الحدث غير موجود")
    
    # Generate invitations data
    invitations_data = []
    prefix = request.guest_name_prefix or "Guest"
    
    for i in range(request.count):
        invitations_data.append({
            "guest_name": f"{prefix} {i+1}",
            "ticket_class": request.ticket_class
        })
    
    # Check quota
    await _check_event_quota(db, str(tenant_id), str(request.event_id), invitations_data)
    
    try:
        # Execute fast generation
        result = await generate_invitations_fast(
            db=db,
            tenant_id=str(tenant_id),
            event_id=str(request.event_id),
            invitations_data=invitations_data,
            layout_config=request.layout_config,
            generate_pdf=request.generate_pdf,
            generate_zip=request.generate_zip,
            upload_individual_barcodes=request.upload_individual_barcodes,
        )
        
        # Log the operation
        await log_audit(
            db, tenant_id=tenant_id, actor_user_id=user.id,
            action="fast_invitations.generate_by_count", resource_type="event",
            resource_id=str(request.event_id),
            metadata={
                "count": request.count,
                "ticket_class": request.ticket_class,
                "generation_time_ms": result.generation_time_ms,
                "total_invitations": result.total_invitations
            }
        )
        await db.commit()
        
        # Prepare response
        response = FastGenerationResponse(
            success=result.success,
            total_invitations=result.total_invitations,
            generation_time_ms=result.generation_time_ms,
            pdf_url=result.pdf_url,
            zip_url=result.zip_url,
            pdf_size_mb=result.pdf_size / (1024*1024) if result.pdf_size else None,
            zip_size_mb=result.zip_size / (1024*1024) if result.zip_size else None,
            error_message=result.error_message
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Fast generation by count failed: {e}")
        raise HTTPException(500, f"فشل في التوليد السريع: {str(e)}")


@router.get("/download/{event_id}/pdf")
async def download_event_pdf(
    event_id: UUID,
    http_request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get download URL for the generated PDF of an event."""
    tenant_id = get_tenant_id_from_header(http_request)
    await require_permission(db, tenant_id, user.id, "invitations.view")
    
    # Get PDF URL from database
    result = await db.execute(
        text("""
            SELECT pdf_url
            FROM invitations 
            WHERE event_id = :eid AND tenant_id = :tid AND pdf_url IS NOT NULL
            GROUP BY pdf_url
            ORDER BY MAX(updated_at) DESC
            LIMIT 1
        """),
        {"eid": str(event_id), "tid": str(tenant_id)}
    )
    
    row = result.first()
    if not row or not row[0]:
        raise HTTPException(404, "ملف PDF غير موجود")
    
    return {"download_url": row[0]}


@router.get("/download/{event_id}/zip")
async def download_event_zip(
    event_id: UUID,
    http_request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get download URL for the generated ZIP of an event."""
    tenant_id = get_tenant_id_from_header(http_request)
    await require_permission(db, tenant_id, user.id, "invitations.view")
    
    # Get ZIP URL from database
    result = await db.execute(
        text("""
            SELECT zip_url
            FROM invitations 
            WHERE event_id = :eid AND tenant_id = :tid AND zip_url IS NOT NULL
            GROUP BY zip_url
            ORDER BY MAX(updated_at) DESC
            LIMIT 1
        """),
        {"eid": str(event_id), "tid": str(tenant_id)}
    )
    
    row = result.first()
    if not row or not row[0]:
        raise HTTPException(404, "ملف ZIP غير موجود")
    
    return {"download_url": row[0]}


@router.get("/history/{event_id}", response_model=List[GenerationHistoryItem])
async def get_generation_history(
    event_id: UUID,
    http_request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List completed fast generation operations for an event."""
    tenant_id = get_tenant_id_from_header(http_request)
    await require_permission(db, tenant_id, user.id, "invitations.view")

    result = await db.execute(
        text("""
            SELECT
                md5(COALESCE(pdf_url, '') || '|' || COALESCE(zip_url, '')) AS id,
                COUNT(*) AS total_invitations,
                COUNT(CASE WHEN ticket_class = 'vip' THEN 1 END) AS vip_count,
                COUNT(CASE WHEN ticket_class = 'normal' THEN 1 END) AS normal_count,
                MAX(updated_at) AS generated_at,
                pdf_url,
                zip_url
            FROM invitations
            WHERE event_id = :eid
              AND tenant_id = :tid
              AND (pdf_url IS NOT NULL OR zip_url IS NOT NULL)
              AND (metadata IS NULL OR metadata->>'generation_deleted' IS DISTINCT FROM 'true')
            GROUP BY pdf_url, zip_url
            ORDER BY MAX(updated_at) DESC
            LIMIT 50
        """),
        {"eid": str(event_id), "tid": str(tenant_id)}
    )

    items = []
    for row in result.mappings().all():
        items.append({
            "id": row["id"],
            "total_invitations": row["total_invitations"],
            "vip_count": row["vip_count"],
            "normal_count": row["normal_count"],
            "generated_at": row["generated_at"].isoformat() if row["generated_at"] else None,
            "pdf_url": row["pdf_url"],
            "zip_url": row["zip_url"],
        })
    return items


@router.get("/history/{event_id}/{operation_id}", response_model=list[InvitationRead])
async def get_generation_operation_details(
    event_id: UUID,
    operation_id: str,
    http_request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all invitations that belong to a given generation operation (by operation id).

    The operation id is the md5 hash of the concatenated pdf_url and zip_url used in the history grouping.
    """
    tenant_id = get_tenant_id_from_header(http_request)
    await require_permission(db, tenant_id, user.id, "invitations.view")

    result = await db.execute(
        text("""
            SELECT *
            FROM invitations
            WHERE event_id = :eid
              AND tenant_id = :tid
              AND md5(COALESCE(pdf_url, '') || '|' || COALESCE(zip_url, '')) = :opid
              AND (metadata IS NULL OR metadata->>'generation_deleted' IS DISTINCT FROM 'true')
            ORDER BY created_at DESC
        """),
        {"eid": str(event_id), "tid": str(tenant_id), "opid": operation_id},
    )

    rows = result.mappings().all()
    return [InvitationRead(**dict(r)) for r in rows]


@router.delete("/history/{event_id}/{operation_id}", response_model=DeleteGenerationResponse)
async def delete_generation_operation(
    event_id: UUID,
    operation_id: str,
    http_request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete one fast generation operation and its invitations."""
    tenant_id = get_tenant_id_from_header(http_request)
    await require_permission(db, tenant_id, user.id, "invitations.revoke")

    operation = await db.execute(
        text("""
            SELECT
                md5(COALESCE(pdf_url, '') || '|' || COALESCE(zip_url, '')) AS id,
                pdf_url,
                zip_url,
                COUNT(*) AS total_invitations
            FROM invitations
            WHERE event_id = :eid
              AND tenant_id = :tid
              AND (pdf_url IS NOT NULL OR zip_url IS NOT NULL)
              AND (metadata IS NULL OR metadata->>'generation_deleted' IS DISTINCT FROM 'true')
            GROUP BY pdf_url, zip_url
            HAVING md5(COALESCE(pdf_url, '') || '|' || COALESCE(zip_url, '')) = :opid
            LIMIT 1
        """),
        {"eid": str(event_id), "tid": str(tenant_id), "opid": operation_id},
    )
    row = operation.mappings().first()
    if not row:
        raise HTTPException(404, "عملية التوليد غير موجودة")

    deleted = await db.execute(
        text("""
            UPDATE invitations SET
                status = 'revoked',
                metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
                    'generation_deleted', true,
                    'generation_deleted_at', now(),
                    'generation_deleted_by', :user_id,
                    'generation_delete_operation_id', :opid
                ),
                updated_at = now()
            WHERE event_id = :eid
              AND tenant_id = :tid
              AND md5(COALESCE(pdf_url, '') || '|' || COALESCE(zip_url, '')) = :opid
              AND (metadata IS NULL OR metadata->>'generation_deleted' IS DISTINCT FROM 'true')
            RETURNING id
        """),
        {
            "eid": str(event_id),
            "tid": str(tenant_id),
            "opid": operation_id,
            "user_id": str(user.id),
        },
    )
    deleted_count = len(deleted.fetchall())

    await log_audit(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id,
        action="fast_invitations.soft_delete_generation",
        resource_type="event",
        resource_id=str(event_id),
        metadata={
            "operation_id": operation_id,
            "soft_deleted_invitations": deleted_count,
        },
        ip_address=http_request.client.host if http_request.client else None,
    )
    await db.commit()

    return {
        "success": True,
        "deleted_invitations": deleted_count,
        "deleted_files": 0,
    }


@router.get("/stats/{event_id}")
async def get_generation_stats(
    event_id: UUID,
    http_request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get generation statistics for an event."""
    tenant_id = get_tenant_id_from_header(http_request)
    await require_permission(db, tenant_id, user.id, "invitations.view")
    
    # Get statistics
    result = await db.execute(
        text("""
            SELECT 
                COUNT(*) as total_invitations,
                COUNT(CASE WHEN qr_data IS NOT NULL THEN 1 END) as generated_barcodes,
                COUNT(CASE WHEN pdf_url IS NOT NULL THEN 1 END) as has_pdf,
                COUNT(CASE WHEN zip_url IS NOT NULL THEN 1 END) as has_zip,
                COUNT(CASE WHEN status = 'sent' THEN 1 END) as sent_count,
                COUNT(CASE WHEN status = 'viewed' THEN 1 END) as viewed_count,
                COUNT(CASE WHEN status = 'accepted' THEN 1 END) as accepted_count,
                COUNT(CASE WHEN ticket_class = 'vip' THEN 1 END) as vip_count,
                COUNT(CASE WHEN ticket_class = 'normal' THEN 1 END) as normal_count,
                MAX(updated_at) as last_generation
            FROM invitations 
            WHERE event_id = :eid AND tenant_id = :tid
              AND (metadata IS NULL OR metadata->>'generation_deleted' IS DISTINCT FROM 'true')
        """),
        {"eid": str(event_id), "tid": str(tenant_id)}
    )
    
    stats = result.mappings().first()
    
    return {
        "event_id": str(event_id),
        "total_invitations": stats["total_invitations"],
        "generated_barcodes": stats["generated_barcodes"],
        "has_pdf": stats["has_pdf"] > 0,
        "has_zip": stats["has_zip"] > 0,
        "sent_count": stats["sent_count"],
        "viewed_count": stats["viewed_count"],
        "accepted_count": stats["accepted_count"],
        "vip_count": stats["vip_count"],
        "normal_count": stats["normal_count"],
        "last_generation": stats["last_generation"],
        "generation_progress": {
            "barcodes": int((stats["generated_barcodes"] / stats["total_invitations"]) * 100) if stats["total_invitations"] > 0 else 0
        }
    }


# ══════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════

async def _check_event_quota(
    db: AsyncSession, tenant_id: str, event_id: str, invitations_data: List[Dict[str, Any]]
):
    """Check if event has quota for the requested invitations."""
    # Count by ticket class
    vip_count = sum(1 for inv in invitations_data if inv.get('ticket_class') == 'vip')
    normal_count = sum(1 for inv in invitations_data if inv.get('ticket_class') == 'normal')
    
    # Get current usage and quotas
    result = await db.execute(
        text("""
            SELECT 
                e.vip_quota,
                e.normal_quota,
                COUNT(CASE WHEN i.ticket_class = 'vip' AND i.status NOT IN ('revoked','expired') THEN 1 END) as vip_used,
                COUNT(CASE WHEN i.ticket_class = 'normal' AND i.status NOT IN ('revoked','expired') THEN 1 END) as normal_used
            FROM events e
            LEFT JOIN invitations i ON i.event_id = e.id
            WHERE e.id = :eid AND e.tenant_id = :tid
            GROUP BY e.id
        """),
        {"eid": event_id, "tid": tenant_id}
    )
    
    row = result.mappings().first()
    if not row:
        raise HTTPException(404, "الحدث غير موجود")
    
    # Check VIP quota
    if row["vip_quota"] > 0 and (row["vip_used"] + vip_count) > row["vip_quota"]:
        raise HTTPException(
            400, 
            f"تم الوصول للحد الأقصى لدعوات VIP ({row['vip_quota']}). "
            f"المستخدم: {row['vip_used']}, المطلوب: {vip_count}"
        )


    # Check normal quota
    if row["normal_quota"] > 0 and (row["normal_used"] + normal_count) > row["normal_quota"]:
        raise HTTPException(
            400,
            f"تم الوصول للحد الأقصى لدعوات Normal ({row['normal_quota']}). "
            f"المستخدم: {row['normal_used']}, المطلوب: {normal_count}"
        )
