-- Migration v17: Team workflows — creation requests + event assignment + visibility
--
-- Adds two request/approval workflows on top of the existing teams model:
--   1) team_requests        — member proposes a team; PLATFORM staff approves.
--   2) event_team_assignments — org admin assigns an event to a team; the team
--                               LEAD accepts/rejects. Acceptance sets events.team_id.
--
-- Event visibility isolation (members see only their teams' events, plus
-- unassigned events) is enforced in the application layer (list_events).

-- ============================================================
-- 1) TEAM CREATION REQUESTS (approved at platform level)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.team_requests (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    requested_by       UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name               TEXT NOT NULL,
    description        TEXT,
    color              TEXT DEFAULT '#6366f1',
    proposed_leader_id UUID REFERENCES public.profiles(id),
    status             TEXT NOT NULL DEFAULT 'pending',  -- pending / approved / rejected
    reviewed_by        UUID REFERENCES public.profiles(id),
    review_note        TEXT,
    reviewed_at        TIMESTAMPTZ,
    created_team_id    UUID REFERENCES public.teams(id) ON DELETE SET NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_team_requests_tenant ON public.team_requests(tenant_id);
CREATE INDEX IF NOT EXISTS idx_team_requests_status ON public.team_requests(status);
CREATE INDEX IF NOT EXISTS idx_team_requests_requested_by ON public.team_requests(requested_by);

-- Only one open (pending) request per (tenant, name).
CREATE UNIQUE INDEX IF NOT EXISTS uq_team_requests_pending_name
    ON public.team_requests(tenant_id, lower(name))
    WHERE status = 'pending';

-- ============================================================
-- 2) EVENT -> TEAM ASSIGNMENTS (accepted by team lead)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.event_team_assignments (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id      UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    team_id       UUID NOT NULL REFERENCES public.teams(id) ON DELETE CASCADE,
    tenant_id     UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    assigned_by   UUID NOT NULL REFERENCES public.profiles(id),
    status        TEXT NOT NULL DEFAULT 'pending',  -- pending / accepted / rejected
    responded_by  UUID REFERENCES public.profiles(id),
    response_note TEXT,
    responded_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(event_id, team_id)
);

CREATE INDEX IF NOT EXISTS idx_eta_tenant ON public.event_team_assignments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_eta_team ON public.event_team_assignments(team_id);
CREATE INDEX IF NOT EXISTS idx_eta_event ON public.event_team_assignments(event_id);
CREATE INDEX IF NOT EXISTS idx_eta_status ON public.event_team_assignments(status);

-- ============================================================
-- 3) NEW PERMISSION KEYS
-- ============================================================
INSERT INTO public.permissions (key, description) VALUES
    ('teams.request',       'طلب إنشاء فريق'),
    ('teams.assign_events', 'إسناد الأحداث للفرق')
ON CONFLICT (key) DO NOTHING;

-- Grant teams.request + teams.assign_events to existing Admin roles
-- (Admin already holds every permission via the provisioning wildcard, but
--  this keeps already-provisioned tenants consistent for the new keys).
INSERT INTO public.role_permissions (role_id, permission_key)
SELECT r.id, p.key
FROM public.roles r
CROSS JOIN (VALUES ('teams.request'), ('teams.assign_events')) AS p(key)
WHERE r.name = 'Admin'
ON CONFLICT DO NOTHING;

-- Grant teams.request to existing Member roles (members may propose teams).
INSERT INTO public.role_permissions (role_id, permission_key)
SELECT r.id, 'teams.request'
FROM public.roles r
WHERE r.name = 'Member'
ON CONFLICT DO NOTHING;

-- ============================================================
-- 4) updated_at triggers (reuse the shared function if present)
-- ============================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'update_updated_at') THEN
        DROP TRIGGER IF EXISTS set_updated_at ON public.team_requests;
        CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.team_requests
            FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();
        DROP TRIGGER IF EXISTS set_updated_at ON public.event_team_assignments;
        CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.event_team_assignments
            FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();
    END IF;
END $$;
