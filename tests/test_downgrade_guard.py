"""
Unit tests for feature_service.check_downgrade_allowed.

Pure-logic tests with a fake DB session (no live server/DB). Verifies that a
plan change is blocked (HTTP 409) when existing usage of persistent resources
exceeds the target plan's limits, and allowed otherwise.

Run:  python -m pytest tests/test_downgrade_guard.py -v
"""
import uuid
import pytest
from fastapi import HTTPException

from app.services import feature_service
from app.services.feature_service import check_downgrade_allowed


class _Result:
    def __init__(self, rows=None, scalar=None):
        self._rows = rows or []
        self._scalar = scalar

    def mappings(self):
        return self

    def all(self):
        return self._rows

    def scalar(self):
        return self._scalar


class FakeSession:
    """Routes execute() by inspecting the SQL text."""

    def __init__(self, target_limits: dict, counts: dict):
        # target_limits: {limit_key: value}; counts: {resource_table: current}
        self._target_limits = target_limits
        self._counts = counts

    async def execute(self, clause, params=None):
        sql = str(clause)
        if "plan_limits" in sql and "p.code" in sql:
            rows = [{"key": k, "limit_value": v} for k, v in self._target_limits.items()]
            return _Result(rows=rows)
        if "FROM memberships" in sql:
            return _Result(scalar=self._counts.get("memberships", 0))
        if "FROM teams" in sql:
            return _Result(scalar=self._counts.get("teams", 0))
        if "FROM guests" in sql:
            return _Result(scalar=self._counts.get("guests", 0))
        raise AssertionError(f"Unexpected SQL routed to FakeSession: {sql[:80]}")


TID = uuid.uuid4()


@pytest.fixture
def patch_storage(monkeypatch):
    """Patch storage byte counter; tests set the MB they want via the value."""
    def _set(mb):
        async def fake(db, tenant_id):
            return mb * 1024 * 1024
        monkeypatch.setattr(feature_service, "get_tenant_storage_bytes", fake)
    return _set


@pytest.mark.asyncio
async def test_downgrade_blocked_when_seats_exceed(patch_storage):
    patch_storage(0)
    db = FakeSession(
        target_limits={"seats_max": 2, "teams_max": 1, "guests_max": 200, "storage_mb": 500},
        counts={"memberships": 5, "teams": 1, "guests": 100},
    )
    with pytest.raises(HTTPException) as exc:
        await check_downgrade_allowed(db, TID, "starter")
    assert exc.value.status_code == 409
    assert "الأعضاء" in exc.value.detail
    assert "5" in exc.value.detail and "2" in exc.value.detail


@pytest.mark.asyncio
async def test_downgrade_blocked_lists_all_violations(patch_storage):
    patch_storage(800)  # over 500 MB limit
    db = FakeSession(
        target_limits={"seats_max": 2, "teams_max": 1, "guests_max": 200, "storage_mb": 500},
        counts={"memberships": 5, "teams": 3, "guests": 300},
    )
    with pytest.raises(HTTPException) as exc:
        await check_downgrade_allowed(db, TID, "starter")
    detail = exc.value.detail
    assert exc.value.status_code == 409
    for label in ("الأعضاء", "الفرق", "الضيوف", "التخزين"):
        assert label in detail


@pytest.mark.asyncio
async def test_downgrade_allowed_when_within_limits(patch_storage):
    patch_storage(100)
    db = FakeSession(
        target_limits={"seats_max": 5, "teams_max": 2, "guests_max": 2000, "storage_mb": 2000},
        counts={"memberships": 3, "teams": 1, "guests": 100},
    )
    # Should not raise.
    await check_downgrade_allowed(db, TID, "basic")


@pytest.mark.asyncio
async def test_unlimited_target_never_blocks(patch_storage):
    patch_storage(999999)
    db = FakeSession(
        target_limits={"seats_max": -1, "teams_max": -1, "guests_max": -1, "storage_mb": -1},
        counts={"memberships": 999, "teams": 999, "guests": 999999},
    )
    await check_downgrade_allowed(db, TID, "enterprise")


@pytest.mark.asyncio
async def test_unknown_plan_is_noop(patch_storage):
    patch_storage(0)
    db = FakeSession(target_limits={}, counts={})
    await check_downgrade_allowed(db, TID, "does-not-exist")


@pytest.mark.asyncio
async def test_boundary_equal_usage_allowed(patch_storage):
    """Usage exactly at the limit is allowed (only strictly-over blocks)."""
    patch_storage(500)
    db = FakeSession(
        target_limits={"seats_max": 2, "teams_max": 1, "guests_max": 200, "storage_mb": 500},
        counts={"memberships": 2, "teams": 1, "guests": 200},
    )
    await check_downgrade_allowed(db, TID, "starter")
