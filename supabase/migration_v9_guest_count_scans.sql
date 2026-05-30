-- ============================================================
-- Migration V9: Guest count per invitation / multi-scan support
-- One barcode may represent multiple people. The scan limit is
-- controlled by invitations.guest_count.
-- ============================================================

ALTER TABLE public.invitations
    ADD COLUMN IF NOT EXISTS guest_count INT NOT NULL DEFAULT 1;

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
BEGIN
    SELECT i.*, e.title AS event_title, e.allow_reentry
    INTO v_inv
    FROM public.invitations i
    JOIN public.events e ON e.id = i.event_id
    WHERE i.token = p_token
    FOR UPDATE OF i;

    IF NOT FOUND THEN
        RETURN QUERY SELECT NULL::UUID, 'invalid'::checkin_result, NULL::TEXT, NULL::ticket_class, NULL::TEXT, 0;
        RETURN;
    END IF;

    IF p_event_id IS NOT NULL AND v_inv.event_id != p_event_id THEN
        RETURN QUERY SELECT v_inv.id, 'wrong_event'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
        RETURN;
    END IF;

    IF v_inv.status = 'revoked' THEN
        RETURN QUERY SELECT v_inv.id, 'revoked'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
        RETURN;
    END IF;

    IF v_inv.status = 'expired' OR (v_inv.expires_at IS NOT NULL AND v_inv.expires_at < now()) THEN
        RETURN QUERY SELECT v_inv.id, 'expired'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
        RETURN;
    END IF;

    IF v_inv.checkin_count >= COALESCE(v_inv.guest_count, 1) AND NOT v_inv.allow_reentry THEN
        RETURN QUERY SELECT v_inv.id, 'already_checked_in'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
        RETURN;
    END IF;

    IF p_gate_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM public.event_gates
            WHERE id = p_gate_id AND v_inv.ticket_class = ANY(allowed_classes)
        ) THEN
            RETURN QUERY SELECT v_inv.id, 'wrong_gate'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
            RETURN;
        END IF;
    END IF;

    UPDATE public.invitations SET
        status = 'checked_in',
        checked_in_at = COALESCE(checked_in_at, now()),
        checkin_count = checkin_count + 1,
        updated_at = now()
    WHERE id = v_inv.id;

    RETURN QUERY SELECT v_inv.id, 'success'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count + 1;
END;
$$;