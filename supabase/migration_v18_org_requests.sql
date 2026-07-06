-- Migration v18: Organization (organizer-team) signup requests
--
-- A public visitor can request to register as an "organizer team". No Supabase
-- auth user or tenant is created up front — the request waits for PLATFORM staff
-- approval. On approval the platform endpoint provisions the user + tenant.
--
-- The applicant's chosen password is stored ENCRYPTED (Fernet, app-layer) and is
-- wiped the moment the request is approved or rejected.

CREATE TABLE IF NOT EXISTS public.organization_requests (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status                   TEXT NOT NULL DEFAULT 'pending',  -- pending / approved / rejected / cancelled

    -- ── Applicant (account-to-be) ──
    full_name                TEXT NOT NULL,
    email                    TEXT NOT NULL,
    phone                    TEXT,
    password_encrypted       TEXT,                 -- Fernet ciphertext; wiped after review

    -- ── Organization ──
    org_name                 TEXT NOT NULL,
    org_type                 TEXT,
    description              TEXT,
    city                     TEXT,
    country                  TEXT,
    website                  TEXT,
    contact_handle           TEXT,

    -- ── Expected activity size ──
    expected_events_per_month INTEGER,
    expected_attendees        INTEGER,
    requested_plan_code       TEXT,

    -- ── Proof / documents ──
    proof_url                TEXT,                 -- proof this is a real organizer team
    documents_url            TEXT,
    notes                    TEXT,

    -- ── Review ──
    reviewed_by              UUID REFERENCES public.profiles(id),
    review_note              TEXT,
    reviewed_at              TIMESTAMPTZ,
    created_tenant_id        UUID REFERENCES public.tenants(id) ON DELETE SET NULL,
    created_user_id          UUID,

    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_org_requests_status ON public.organization_requests(status);
CREATE INDEX IF NOT EXISTS idx_org_requests_email  ON public.organization_requests(lower(email));

-- Only one open (pending) request per email.
CREATE UNIQUE INDEX IF NOT EXISTS uq_org_requests_pending_email
    ON public.organization_requests(lower(email))
    WHERE status = 'pending';

-- updated_at trigger (reuse the shared function if present)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'update_updated_at') THEN
        DROP TRIGGER IF EXISTS set_updated_at ON public.organization_requests;
        CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.organization_requests
            FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();
    END IF;
END $$;
