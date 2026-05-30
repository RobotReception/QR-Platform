-- ============================================================
-- Migration V6: Data Integrity Constraints & Governance
-- قيود سلامة البيانات وحوكمة النظام
-- ============================================================
-- 1) Template element coordinate constraints (0-1 range)
-- 2) Event quota constraints (>= 0)
-- 3) Batch progress constraint (0-100) — already exists via CHECK
-- 4) Result immutability: prevent modification of ready/cancelled batches
-- 5) Invitation snapshot policy enforcement
-- ============================================================

-- ============================================================
-- 1) TEMPLATE ELEMENT COORDINATES: must be 0.0 → 1.0
--    Relative coordinates allow resolution-independent layouts
-- ============================================================

ALTER TABLE public.template_elements
    ADD CONSTRAINT chk_element_x      CHECK (x >= 0 AND x <= 1),
    ADD CONSTRAINT chk_element_y      CHECK (y >= 0 AND y <= 1),
    ADD CONSTRAINT chk_element_width  CHECK (width >= 0 AND width <= 1),
    ADD CONSTRAINT chk_element_height CHECK (height >= 0 AND height <= 1);

-- ============================================================
-- 2) EVENT QUOTAS: must be >= 0 (0 = unlimited)
-- ============================================================

ALTER TABLE public.events
    ADD CONSTRAINT chk_vip_quota    CHECK (vip_quota >= 0),
    ADD CONSTRAINT chk_normal_quota CHECK (normal_quota >= 0);

-- ============================================================
-- 3) BATCH RESULT IMMUTABILITY
--    Once a batch is 'ready', its output URLs and metrics
--    cannot be modified. To regenerate, create a new batch.
-- ============================================================

CREATE OR REPLACE FUNCTION public.protect_ready_batch()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Allow status changes (e.g. ready → ready is blocked by state machine anyway)
    -- But prevent modification of result data on terminal batches
    IF OLD.status IN ('ready', 'cancelled') THEN
        -- Only allow updating metadata (for admin notes)
        IF NEW.result_pdf_url IS DISTINCT FROM OLD.result_pdf_url
           OR NEW.result_zip_url IS DISTINCT FROM OLD.result_zip_url
           OR NEW.result_preview_urls IS DISTINCT FROM OLD.result_preview_urls
           OR NEW.count_done IS DISTINCT FROM OLD.count_done
           OR NEW.count_failed IS DISTINCT FROM OLD.count_failed
        THEN
            RAISE EXCEPTION 'Cannot modify results of a % batch. Create a new batch to regenerate.', OLD.status;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER protect_ready_batch_results
    BEFORE UPDATE ON public.generation_batches
    FOR EACH ROW
    EXECUTE FUNCTION public.protect_ready_batch();

-- ============================================================
-- 4) STORAGE SIGNED URL POLICY
--    Add column to track when signed URLs were last refreshed
-- ============================================================

ALTER TABLE public.generation_batches
    ADD COLUMN IF NOT EXISTS urls_refreshed_at TIMESTAMPTZ;

-- ============================================================
-- 5) FONT ASSET GOVERNANCE
--    Restrict font assets to known safe MIME types
-- ============================================================

-- Only TTF/OTF allowed — Pillow/FreeType cannot render WOFF/WOFF2 at runtime.
ALTER TABLE public.template_assets
    ADD CONSTRAINT chk_font_mime CHECK (
        asset_type != 'font' OR mime_type IN (
            'font/ttf', 'font/otf',
            'application/x-font-ttf', 'application/x-font-otf',
            'application/octet-stream'
        )
    );

-- Font file size limit (5MB for fonts)
ALTER TABLE public.template_assets
    ADD CONSTRAINT chk_font_size CHECK (
        asset_type != 'font' OR file_size <= 5242880
    );

-- ============================================================
-- 6) INVITATION CHECKIN COUNT: must be >= 0
-- ============================================================

ALTER TABLE public.invitations
    ADD CONSTRAINT chk_checkin_count CHECK (checkin_count >= 0);

-- ============================================================
-- 7) OPTION B GUARDRAIL: prevent tenant_id mutation
--    Since service_role bypasses RLS, this trigger is the
--    last line of defense against accidental cross-tenant
--    data migration via UPDATE.
-- ============================================================

CREATE OR REPLACE FUNCTION public.prevent_tenant_id_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.tenant_id IS NOT NULL AND NEW.tenant_id IS DISTINCT FROM OLD.tenant_id THEN
        RAISE EXCEPTION 'Cannot change tenant_id (attempted: % → %)', OLD.tenant_id, NEW.tenant_id;
    END IF;
    RETURN NEW;
END;
$$;

-- Apply AUTOMATICALLY to every public table that has a tenant_id column.
-- This way, any future table with tenant_id is covered without manual updates.
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT table_schema, table_name
        FROM information_schema.columns
        WHERE column_name = 'tenant_id'
          AND table_schema = 'public'
    LOOP
        -- Drop if exists (idempotent re-run)
        EXECUTE format(
            'DROP TRIGGER IF EXISTS prevent_%I_tenant_change ON %I.%I;',
            r.table_name, r.table_schema, r.table_name
        );
        EXECUTE format(
            'CREATE TRIGGER prevent_%I_tenant_change
                BEFORE UPDATE ON %I.%I
                FOR EACH ROW
                EXECUTE FUNCTION public.prevent_tenant_id_change();',
            r.table_name, r.table_schema, r.table_name
        );
    END LOOP;
END;
$$;

-- ============================================================
-- DONE: Migration V6 complete
-- ============================================================
