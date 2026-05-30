-- ============================================================
-- Migration V5: Production Hardening
-- تحسينات أمنية وأداء لبيئة الإنتاج
-- ============================================================
-- 1) Atomic check-in with SELECT FOR UPDATE (race condition fix)
-- 2) Batch state machine constraints
-- 3) Brute-force protection index
-- 4) Batch metrics columns
-- ============================================================

-- ============================================================
-- 1) ATOMIC CHECK-IN: SELECT ... FOR UPDATE
--    Prevents double check-in when multiple scanners hit
--    the same invitation simultaneously.
-- ============================================================

CREATE OR REPLACE FUNCTION public.validate_checkin(
    p_token TEXT,
    p_event_id UUID DEFAULT NULL,
    p_gate_id UUID DEFAULT NULL
)
RETURNS TABLE (
    invitation_id UUID,
    result checkin_result,
    guest_name TEXT,
    ticket_class ticket_class,
    event_title TEXT,
    checkin_count INT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_inv RECORD;
    v_result checkin_result;
BEGIN
    -- Lock the invitation row to prevent concurrent check-in race conditions.
    -- FOR UPDATE ensures only one transaction can validate+update at a time.
    SELECT i.*, e.title AS event_title, e.allow_reentry
    INTO v_inv
    FROM public.invitations i
    JOIN public.events e ON e.id = i.event_id
    WHERE i.token = p_token
    FOR UPDATE OF i;  -- row-level lock on invitations only

    IF NOT FOUND THEN
        RETURN QUERY SELECT NULL::UUID, 'invalid'::checkin_result, NULL::TEXT, NULL::ticket_class, NULL::TEXT, 0;
        RETURN;
    END IF;

    -- Check event match
    IF p_event_id IS NOT NULL AND v_inv.event_id != p_event_id THEN
        RETURN QUERY SELECT v_inv.id, 'wrong_event'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
        RETURN;
    END IF;

    -- Check revoked
    IF v_inv.status = 'revoked' THEN
        RETURN QUERY SELECT v_inv.id, 'revoked'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
        RETURN;
    END IF;

    -- Check expired
    IF v_inv.status = 'expired' OR (v_inv.expires_at IS NOT NULL AND v_inv.expires_at < now()) THEN
        RETURN QUERY SELECT v_inv.id, 'expired'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
        RETURN;
    END IF;

    -- Check already checked in (atomic: the FOR UPDATE lock guarantees
    -- no other transaction can read stale checkin_count)
    IF v_inv.checkin_count >= COALESCE(v_inv.guest_count, 1) AND NOT v_inv.allow_reentry THEN
        RETURN QUERY SELECT v_inv.id, 'already_checked_in'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
        RETURN;
    END IF;

    -- Check gate class
    IF p_gate_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM public.event_gates
            WHERE id = p_gate_id AND v_inv.ticket_class = ANY(allowed_classes)
        ) THEN
            RETURN QUERY SELECT v_inv.id, 'wrong_gate'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
            RETURN;
        END IF;
    END IF;

    -- SUCCESS: atomically update the invitation within the same lock
    UPDATE public.invitations SET
        status = 'checked_in',
        checked_in_at = COALESCE(checked_in_at, now()),
        checkin_count = checkin_count + 1,
        updated_at = now()
    WHERE id = v_inv.id;

    RETURN QUERY SELECT v_inv.id, 'success'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count + 1;
END;
$$;

-- ============================================================
-- 2) BATCH STATE MACHINE: valid transitions only
--    Prevents invalid status jumps (e.g. ready → generating)
-- ============================================================

CREATE OR REPLACE FUNCTION public.enforce_batch_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    valid BOOLEAN := false;
BEGIN
    -- Allow any transition if old status is NULL (new row)
    IF OLD.status IS NULL THEN
        RETURN NEW;
    END IF;

    -- Define valid transitions
    CASE OLD.status
        WHEN 'draft' THEN
            valid := NEW.status IN ('queued', 'cancelled');
        WHEN 'queued' THEN
            valid := NEW.status IN ('generating_barcodes', 'cancelled', 'failed');
        WHEN 'generating_barcodes' THEN
            valid := NEW.status IN ('rendering_images', 'generating_pdf', 'cancelled', 'failed');
        WHEN 'rendering_images' THEN
            valid := NEW.status IN ('generating_pdf', 'cancelled', 'failed');
        WHEN 'generating_pdf' THEN
            valid := NEW.status IN ('generating_zip', 'cancelled', 'failed');
        WHEN 'generating_zip' THEN
            valid := NEW.status IN ('ready', 'cancelled', 'failed');
        WHEN 'ready' THEN
            valid := false;  -- terminal state
        WHEN 'failed' THEN
            valid := NEW.status IN ('queued');  -- retry requeues
        WHEN 'cancelled' THEN
            valid := false;  -- terminal state
        ELSE
            valid := false;
    END CASE;

    IF NOT valid THEN
        RAISE EXCEPTION 'Invalid batch status transition: % → %', OLD.status, NEW.status;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER enforce_batch_status_transition
    BEFORE UPDATE OF status ON public.generation_batches
    FOR EACH ROW
    EXECUTE FUNCTION public.enforce_batch_transition();

-- ============================================================
-- 3) BRUTE-FORCE PROTECTION: index for rate limiting lookups
-- ============================================================

-- Fast lookup for recent failed scan attempts by IP (for rate limiting)
CREATE INDEX IF NOT EXISTS idx_checkins_ip_recent
    ON public.checkins (ip_address, created_at DESC)
    WHERE result != 'success';

-- ============================================================
-- 4) BATCH METRICS: track timing and sizes
-- ============================================================

ALTER TABLE public.generation_batches
    ADD COLUMN IF NOT EXISTS started_at      TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS completed_at    TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS duration_ms     BIGINT,
    ADD COLUMN IF NOT EXISTS result_pdf_size BIGINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS result_zip_size BIGINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS error_summary   JSONB DEFAULT '{}';

-- ============================================================
-- 5) FONT ASSET REFERENCE: link elements to uploaded fonts
-- ============================================================

ALTER TABLE public.template_elements
    ADD COLUMN IF NOT EXISTS font_asset_id UUID REFERENCES public.template_assets(id) ON DELETE SET NULL;

-- ============================================================
-- DONE: Migration V5 complete
-- ============================================================
