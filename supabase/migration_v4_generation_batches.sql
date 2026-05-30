-- ============================================================
-- Migration V4: Generation Batches + Asset Pipeline
-- نظام توليد الباركود والصور وPDF/ZIP
-- ============================================================
-- New tables: generation_batches, batch_items
-- New columns on invitations: barcode_svg_url, barcode_png_url,
--   render_image_url, barcode_payload, barcode_signature
-- New enum: batch_status
-- New permissions: batches.create, batches.view, batches.manage
-- ============================================================

-- ============================================================
-- 1) ENUM: batch_status
-- ============================================================

CREATE TYPE batch_status AS ENUM (
    'draft',      -- تم الإنشاء ولم يبدأ
    'queued',     -- في الانتظار
    'generating_barcodes',  -- توليد الباركود
    'rendering_images',     -- تركيب الصور (DESIGNED فقط)
    'generating_pdf',       -- إنشاء PDF
    'generating_zip',       -- إنشاء ZIP
    'ready',      -- جاهز للتحميل
    'failed',     -- فشل
    'cancelled'   -- ملغى
);

-- ============================================================
-- 2) TABLE: generation_batches (دفعات التوليد)
-- ============================================================

CREATE TABLE public.generation_batches (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    event_id        UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    template_id     UUID REFERENCES public.invite_templates(id),

    -- Batch config
    mode            template_type NOT NULL DEFAULT 'quick',  -- quick / designed
    ticket_class    ticket_class NOT NULL DEFAULT 'normal',

    -- Counts
    count_total     INT NOT NULL DEFAULT 0,
    count_done      INT NOT NULL DEFAULT 0,
    count_failed    INT NOT NULL DEFAULT 0,

    -- PDF layout settings
    layout_json     JSONB NOT NULL DEFAULT '{
        "page_size": "A4",
        "orientation": "portrait",
        "rows": 5,
        "cols": 5,
        "margin_top_mm": 10,
        "margin_bottom_mm": 10,
        "margin_left_mm": 10,
        "margin_right_mm": 10,
        "gap_x_mm": 2,
        "gap_y_mm": 2,
        "barcode_size_px": 400,
        "show_code_text": true,
        "show_guest_name": true,
        "dpi": 300
    }',

    -- Output settings
    output_formats  TEXT[] NOT NULL DEFAULT '{pdf,zip}',  -- pdf, zip, or both
    barcode_format  TEXT NOT NULL DEFAULT 'qr',           -- qr, barcode128, datamatrix

    -- Status & progress
    status          batch_status NOT NULL DEFAULT 'draft',
    progress        INT NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,

    -- Result URLs (stored in Supabase Storage)
    result_pdf_url  TEXT,
    result_zip_url  TEXT,
    result_preview_urls TEXT[] DEFAULT '{}',  -- أول 5 صور للمعاينة

    -- Meta
    created_by      UUID REFERENCES public.profiles(id),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_gen_batches_tenant ON public.generation_batches(tenant_id);
CREATE INDEX idx_gen_batches_event ON public.generation_batches(event_id);
CREATE INDEX idx_gen_batches_status ON public.generation_batches(status);
CREATE INDEX idx_gen_batches_created ON public.generation_batches(created_at DESC);

-- ============================================================
-- 3) TABLE: batch_items (عناصر الدفعة — تتبع مفصل)
-- ============================================================

CREATE TABLE public.batch_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id        UUID NOT NULL REFERENCES public.generation_batches(id) ON DELETE CASCADE,
    invitation_id   UUID NOT NULL REFERENCES public.invitations(id) ON DELETE CASCADE,

    -- Per-item status
    render_status   TEXT NOT NULL DEFAULT 'pending',  -- pending, done, failed, skipped
    error_message   TEXT,

    -- Per-item output
    barcode_url     TEXT,
    render_url      TEXT,

    -- Timing
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_batch_items_batch ON public.batch_items(batch_id);
CREATE INDEX idx_batch_items_invitation ON public.batch_items(invitation_id);
CREATE INDEX idx_batch_items_status ON public.batch_items(render_status);

-- ============================================================
-- 4) ADD COLUMNS TO invitations (أصول الباركود والصورة)
-- ============================================================

ALTER TABLE public.invitations
    ADD COLUMN IF NOT EXISTS barcode_svg_url   TEXT,
    ADD COLUMN IF NOT EXISTS barcode_png_url   TEXT,
    ADD COLUMN IF NOT EXISTS render_image_url  TEXT,
    ADD COLUMN IF NOT EXISTS barcode_payload   TEXT,
    ADD COLUMN IF NOT EXISTS barcode_signature TEXT;

-- Add data_key to template_elements for dynamic data resolution
-- data_key maps element to data source: invite.barcode_payload, guest.name, event.title, etc.
ALTER TABLE public.template_elements
    ADD COLUMN IF NOT EXISTS data_key TEXT;

-- Add custom_fields to guests for extra dynamic data (date1, date2, seat, etc.)
ALTER TABLE public.guests
    ADD COLUMN IF NOT EXISTS custom_fields JSONB DEFAULT '{}';

-- ============================================================
-- 5) TRIGGERS
-- ============================================================

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.generation_batches
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- ============================================================
-- 6) RLS
-- ============================================================

ALTER TABLE public.generation_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.batch_items ENABLE ROW LEVEL SECURITY;

-- Batches
CREATE POLICY "Members can view batches" ON public.generation_batches
    FOR SELECT USING (tenant_id IN (SELECT public.get_my_tenant_ids()));
CREATE POLICY "Admins can manage batches" ON public.generation_batches
    FOR ALL USING (public.is_admin_of(tenant_id));

-- Batch items
CREATE POLICY "Members can view batch items" ON public.batch_items
    FOR SELECT USING (
        batch_id IN (SELECT id FROM public.generation_batches WHERE tenant_id IN (SELECT public.get_my_tenant_ids()))
    );
CREATE POLICY "Admins can manage batch items" ON public.batch_items
    FOR ALL USING (
        batch_id IN (SELECT id FROM public.generation_batches WHERE public.is_admin_of(tenant_id))
    );

-- ============================================================
-- 7) NEW PERMISSIONS
-- ============================================================

INSERT INTO public.permissions (key, description) VALUES
    ('batches.create',  'إنشاء دفعة توليد'),
    ('batches.view',    'عرض دفعات التوليد'),
    ('batches.manage',  'إدارة دفعات التوليد (إلغاء/إعادة)')
ON CONFLICT (key) DO NOTHING;

-- Add to existing roles
-- Admin already gets all permissions
-- Member gets create + view
INSERT INTO public.role_permissions (role_id, permission_key)
SELECT r.id, p.key
FROM public.roles r, public.permissions p
WHERE r.is_system_role = true
  AND r.name = 'Admin'
  AND p.key IN ('batches.create', 'batches.view', 'batches.manage')
ON CONFLICT DO NOTHING;

INSERT INTO public.role_permissions (role_id, permission_key)
SELECT r.id, p.key
FROM public.roles r, public.permissions p
WHERE r.is_system_role = true
  AND r.name = 'Member'
  AND p.key IN ('batches.create', 'batches.view')
ON CONFLICT DO NOTHING;

INSERT INTO public.role_permissions (role_id, permission_key)
SELECT r.id, p.key
FROM public.roles r, public.permissions p
WHERE r.is_system_role = true
  AND r.name = 'Viewer'
  AND p.key IN ('batches.view')
ON CONFLICT DO NOTHING;

-- ============================================================
-- 8) STORAGE BUCKET (Supabase Storage)
-- ============================================================
-- Run this in Supabase Dashboard > Storage or via API:
-- CREATE BUCKET: 'invitations' (private)
-- Policies:
--   - Authenticated users can upload to their org path
--   - Service role can do everything

-- ============================================================
-- 9) HELPER: Update batch progress
-- ============================================================

CREATE OR REPLACE FUNCTION public.update_batch_progress(p_batch_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_total INT;
    v_done INT;
    v_failed INT;
    v_progress INT;
BEGIN
    SELECT count_total INTO v_total FROM generation_batches WHERE id = p_batch_id;

    SELECT
        COUNT(*) FILTER (WHERE render_status = 'done'),
        COUNT(*) FILTER (WHERE render_status = 'failed')
    INTO v_done, v_failed
    FROM batch_items WHERE batch_id = p_batch_id;

    IF v_total > 0 THEN
        v_progress := ((v_done + v_failed) * 100) / v_total;
    ELSE
        v_progress := 0;
    END IF;

    UPDATE generation_batches
    SET count_done = v_done,
        count_failed = v_failed,
        progress = LEAST(v_progress, 100),
        updated_at = now()
    WHERE id = p_batch_id;
END;
$$;

-- ============================================================
-- DONE: Migration V4 complete
-- ============================================================
