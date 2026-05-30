"""
Tenant-Scoped Query Helpers (Option B Guardrail — Enforced Query Pattern).

All tenant-scoped database operations MUST go through these helpers to guarantee
that every query includes WHERE tenant_id = :tenant_id.

Usage in routes:
    from app.services.tenant_query import TenantQuery

    tq = TenantQuery(db, tenant_id)
    rows = await tq.select("events", columns="id, title, status")
    row  = await tq.select_one("events", where="id = :id", params={"id": eid})
    await tq.update("events", set_clause="title = :t", params={"t": "New"}, where="id = :id", extra={"id": eid})
    await tq.delete("events", where="id = :id", params={"id": eid})
    await tq.insert("events", columns=["title", "tenant_id"], values={"title": "X", "tenant_id": str(tenant_id)})

Public token endpoints (view/rsvp) bypass this — they query by token only
and return guest-safe fields. That is the ONLY exception.
"""
import logging
from uuid import UUID
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TenantQuery:
    """Enforces tenant_id in every query. Prevents accidental cross-tenant access."""

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        if not tenant_id:
            raise ValueError("tenant_id is required for TenantQuery")
        self.db = db
        self.tenant_id = str(tenant_id)

    async def select(
        self,
        table: str,
        columns: str = "*",
        where: str = "",
        params: Optional[dict[str, Any]] = None,
        order_by: str = "",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        """SELECT with mandatory tenant_id filter."""
        sql = f"SELECT {columns} FROM {table} WHERE tenant_id = :_tenant_id"
        if where:
            sql += f" AND ({where})"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        if offset is not None:
            sql += f" OFFSET {int(offset)}"

        all_params = {"_tenant_id": self.tenant_id}
        if params:
            all_params.update(params)

        result = await self.db.execute(text(sql), all_params)
        return result.mappings().all()

    async def select_one(
        self,
        table: str,
        columns: str = "*",
        where: str = "",
        params: Optional[dict[str, Any]] = None,
    ):
        """SELECT single row with mandatory tenant_id filter. Returns None if not found."""
        sql = f"SELECT {columns} FROM {table} WHERE tenant_id = :_tenant_id"
        if where:
            sql += f" AND ({where})"
        sql += " LIMIT 1"

        all_params = {"_tenant_id": self.tenant_id}
        if params:
            all_params.update(params)

        result = await self.db.execute(text(sql), all_params)
        return result.mappings().first()

    async def update(
        self,
        table: str,
        set_clause: str,
        where: str = "",
        params: Optional[dict[str, Any]] = None,
    ) -> int:
        """UPDATE with mandatory tenant_id filter. Returns affected row count."""
        sql = f"UPDATE {table} SET {set_clause} WHERE tenant_id = :_tenant_id"
        if where:
            sql += f" AND ({where})"

        all_params = {"_tenant_id": self.tenant_id}
        if params:
            all_params.update(params)

        result = await self.db.execute(text(sql), all_params)
        return result.rowcount

    async def delete(
        self,
        table: str,
        where: str = "",
        params: Optional[dict[str, Any]] = None,
    ) -> int:
        """DELETE with mandatory tenant_id filter. Returns affected row count."""
        sql = f"DELETE FROM {table} WHERE tenant_id = :_tenant_id"
        if where:
            sql += f" AND ({where})"

        all_params = {"_tenant_id": self.tenant_id}
        if params:
            all_params.update(params)

        result = await self.db.execute(text(sql), all_params)
        return result.rowcount

    async def insert(
        self,
        table: str,
        columns: list[str],
        values: dict[str, Any],
    ):
        """INSERT with tenant_id enforcement.

        If 'tenant_id' is not in columns, it is added automatically.
        If 'tenant_id' IS in values but differs from self.tenant_id, raises ValueError.
        """
        if "tenant_id" in values and values["tenant_id"] != self.tenant_id:
            raise ValueError(
                f"INSERT tenant_id mismatch: got {values['tenant_id']}, "
                f"expected {self.tenant_id}"
            )

        if "tenant_id" not in columns:
            columns = ["tenant_id"] + list(columns)
        values["tenant_id"] = self.tenant_id

        cols_str = ", ".join(columns)
        vals_str = ", ".join(f":{c}" for c in columns)
        sql = f"INSERT INTO {table} ({cols_str}) VALUES ({vals_str}) RETURNING *"

        result = await self.db.execute(text(sql), values)
        return result.mappings().first()

    async def count(
        self,
        table: str,
        where: str = "",
        params: Optional[dict[str, Any]] = None,
    ) -> int:
        """COUNT with mandatory tenant_id filter."""
        sql = f"SELECT COUNT(*) as cnt FROM {table} WHERE tenant_id = :_tenant_id"
        if where:
            sql += f" AND ({where})"

        all_params = {"_tenant_id": self.tenant_id}
        if params:
            all_params.update(params)

        result = await self.db.execute(text(sql), all_params)
        row = result.mappings().first()
        return row["cnt"] if row else 0

    async def exists(
        self,
        table: str,
        where: str = "",
        params: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Check existence with mandatory tenant_id filter."""
        sql = f"SELECT 1 FROM {table} WHERE tenant_id = :_tenant_id"
        if where:
            sql += f" AND ({where})"
        sql += " LIMIT 1"

        all_params = {"_tenant_id": self.tenant_id}
        if params:
            all_params.update(params)

        result = await self.db.execute(text(sql), all_params)
        return result.first() is not None
