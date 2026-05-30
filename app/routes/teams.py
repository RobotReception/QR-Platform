"""Teams API: CRUD + member management."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.auth import get_current_user, get_tenant_id_from_header, CurrentUser
from app.database import get_db
from app.models.team import TeamCreate, TeamRead, TeamUpdate, TeamMemberRead, TeamMemberAdd
from app.services.permission_service import require_permission
from app.services.audit_service import log_audit

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("", response_model=list[TeamRead])
async def list_teams(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "teams.view")

    result = await db.execute(
        text("""
            SELECT t.*, 
                   (SELECT COUNT(*) FROM team_memberships tm WHERE tm.team_id = t.id) as members_count,
                   (SELECT p.full_name FROM team_memberships tm JOIN profiles p ON p.id = tm.user_id WHERE tm.team_id = t.id AND tm.role = 'team_lead' LIMIT 1) as leader_name
            FROM teams t 
            WHERE t.tenant_id = :tid 
            ORDER BY t.name
        """),
        {"tid": str(tenant_id)},
    )
    return [TeamRead(**dict(r)) for r in result.mappings().all()]


@router.post("", response_model=TeamRead, status_code=201)
async def create_team(
    body: TeamCreate, request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "teams.manage")

    leader_id = body.leader_id or user.id

    # Verify leader is in org
    check_leader = await db.execute(
        text("SELECT 1 FROM memberships WHERE tenant_id = :tid AND user_id = :uid AND status = 'active'"),
        {"tid": str(tenant_id), "uid": str(leader_id)},
    )
    if not check_leader.first():
        raise HTTPException(400, "قائد الفريق ليس عضواً نشطاً في المؤسسة")

    # Verify all members are in org
    if body.member_ids:
        for mid in body.member_ids:
            check_member = await db.execute(
                text("SELECT 1 FROM memberships WHERE tenant_id = :tid AND user_id = :uid AND status = 'active'"),
                {"tid": str(tenant_id), "uid": str(mid)},
            )
            if not check_member.first():
                raise HTTPException(400, f"المستخدم ليس عضواً نشطاً في المؤسسة")

    result = await db.execute(
        text("""
            INSERT INTO teams (tenant_id, name, description, color, created_by)
            VALUES (:tid, :name, :desc, :color, :uid)
            RETURNING *
        """),
        {"tid": str(tenant_id), "name": body.name, "desc": body.description, "color": body.color, "uid": str(user.id)},
    )
    row = dict(result.mappings().first())
    team_id = row["id"]

    # Insert Leader
    await db.execute(
        text("""
            INSERT INTO team_memberships (team_id, user_id, role)
            VALUES (:tid, :uid, 'team_lead')
            ON CONFLICT (team_id, user_id) DO UPDATE SET role = 'team_lead'
        """),
        {"tid": str(team_id), "uid": str(leader_id)}
    )

    # Insert Members
    if body.member_ids:
        for mid in body.member_ids:
            if str(mid) != str(leader_id):
                await db.execute(
                    text("""
                        INSERT INTO team_memberships (team_id, user_id, role)
                        VALUES (:tid, :uid, 'member')
                        ON CONFLICT DO NOTHING
                    """),
                    {"tid": str(team_id), "uid": str(mid)}
                )

    await log_audit(db, tenant_id=tenant_id, actor_user_id=user.id,
                    action="team.create", resource_type="team", resource_id=str(team_id),
                    ip_address=request.client.host if request.client else None)
    
    # Fetch computed fields for the response
    leader_info = await db.execute(
        text("SELECT p.full_name FROM profiles p WHERE p.id = :uid"),
        {"uid": str(leader_id)}
    )
    leader_name = leader_info.scalar()
    
    members_count = 1 + (len([m for m in (body.member_ids or []) if str(m) != str(leader_id)]) if body.member_ids else 0)
    
    row["members_count"] = members_count
    row["leader_name"] = leader_name

    await db.commit()
    return TeamRead(**row)


@router.get("/{team_id}", response_model=TeamRead)
async def get_team(
    team_id: UUID, request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "teams.view")

    result = await db.execute(
        text("""
            SELECT t.*, 
                   (SELECT COUNT(*) FROM team_memberships tm WHERE tm.team_id = t.id) as members_count,
                   (SELECT p.full_name FROM team_memberships tm JOIN profiles p ON p.id = tm.user_id WHERE tm.team_id = t.id AND tm.role = 'team_lead' LIMIT 1) as leader_name
            FROM teams t 
            WHERE t.id = :id AND t.tenant_id = :tid
        """),
        {"id": str(team_id), "tid": str(tenant_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(404, "الفريق غير موجود")
    return TeamRead(**dict(row))


@router.patch("/{team_id}", response_model=TeamRead)
async def update_team(
    team_id: UUID, body: TeamUpdate, request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "teams.manage")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, "لا توجد حقول للتعديل")

    set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = str(team_id)
    updates["tid"] = str(tenant_id)

    result = await db.execute(
        text(f"UPDATE teams SET {set_clauses}, updated_at = now() WHERE id = :id AND tenant_id = :tid RETURNING *"),
        updates,
    )
    raw_row = result.mappings().first()
    if not raw_row:
        raise HTTPException(404, "الفريق غير موجود")
        
    row = dict(raw_row)

    # Fetch computed fields
    stats = await db.execute(
        text("""
            SELECT 
                (SELECT COUNT(*) FROM team_memberships WHERE team_id = :tid) as members_count,
                (SELECT p.full_name FROM team_memberships tm JOIN profiles p ON p.id = tm.user_id WHERE tm.team_id = :tid AND tm.role = 'team_lead' LIMIT 1) as leader_name
        """),
        {"tid": str(team_id)}
    )
    stat_row = stats.mappings().first()
    if stat_row:
        row["members_count"] = stat_row["members_count"]
        row["leader_name"] = stat_row["leader_name"]

    await db.commit()
    return TeamRead(**row)


@router.delete("/{team_id}", status_code=204)
async def delete_team(
    team_id: UUID, request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "teams.manage")

    result = await db.execute(
        text("DELETE FROM teams WHERE id = :id AND tenant_id = :tid"),
        {"id": str(team_id), "tid": str(tenant_id)},
    )
    if result.rowcount == 0:
        raise HTTPException(404, "الفريق غير موجود")
    await log_audit(db, tenant_id=tenant_id, actor_user_id=user.id,
                    action="team.delete", resource_type="team", resource_id=str(team_id),
                    ip_address=request.client.host if request.client else None)
    await db.commit()


# ══════════════════════════════════════════════
# TEAM MEMBERS
# ══════════════════════════════════════════════

@router.get("/{team_id}/members", response_model=list[TeamMemberRead])
async def list_team_members(
    team_id: UUID, request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "teams.view")

    result = await db.execute(
        text("""
            SELECT tm.id, tm.team_id, tm.user_id, tm.role, tm.joined_at,
                   p.full_name, p.avatar_url
            FROM team_memberships tm
            JOIN profiles p ON p.id = tm.user_id
            JOIN teams t ON t.id = tm.team_id
            WHERE tm.team_id = :tid AND t.tenant_id = :org
            ORDER BY tm.joined_at
        """),
        {"tid": str(team_id), "org": str(tenant_id)},
    )
    return [TeamMemberRead(**dict(r)) for r in result.mappings().all()]


@router.post("/{team_id}/members", response_model=TeamMemberRead, status_code=201)
async def add_team_member(
    team_id: UUID, body: TeamMemberAdd, request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "teams.manage")

    # Verify user is a member of the org
    check = await db.execute(
        text("SELECT 1 FROM memberships WHERE tenant_id = :tid AND user_id = :uid AND status = 'active'"),
        {"tid": str(tenant_id), "uid": str(body.user_id)},
    )
    if not check.first():
        raise HTTPException(400, "المستخدم ليس عضواً في المؤسسة")

    result = await db.execute(
        text("""
            INSERT INTO team_memberships (team_id, user_id, role)
            VALUES (:tid, :uid, :role)
            ON CONFLICT (team_id, user_id) DO UPDATE SET role = :role
            RETURNING id, team_id, user_id, role, joined_at
        """),
        {"tid": str(team_id), "uid": str(body.user_id), "role": body.role},
    )
    row = result.mappings().first()

    # Get profile info
    p = await db.execute(
        text("SELECT full_name, avatar_url FROM profiles WHERE id = :uid"),
        {"uid": str(body.user_id)},
    )
    profile = p.mappings().first()

    await db.commit()
    return TeamMemberRead(
        **dict(row),
        full_name=profile["full_name"] if profile else None,
        avatar_url=profile["avatar_url"] if profile else None,
    )


@router.delete("/{team_id}/members/{user_id}", status_code=204)
async def remove_team_member(
    team_id: UUID, user_id: UUID, request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "teams.manage")

    result = await db.execute(
        text("DELETE FROM team_memberships WHERE team_id = :tid AND user_id = :uid"),
        {"tid": str(team_id), "uid": str(user_id)},
    )
    if result.rowcount == 0:
        raise HTTPException(404, "العضو غير موجود في الفريق")
    await db.commit()
