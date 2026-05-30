-- ============================================================
-- Migration V5: Fix Missing Columns on Invitations
-- إصلاح الأعمدة المفقودة لعملية إنشاء الدعوات
-- ============================================================
-- Ensures all columns referenced by the backend exist.
-- Safe to run multiple times (IF NOT EXISTS).
-- ============================================================

-- 1) Barcode columns (from V4 migration, re-applied for safety)
ALTER TABLE public.invitations
    ADD COLUMN IF NOT EXISTS barcode_svg_url   TEXT,
    ADD COLUMN IF NOT EXISTS barcode_png_url   TEXT,
    ADD COLUMN IF NOT EXISTS render_image_url  TEXT,
    ADD COLUMN IF NOT EXISTS barcode_payload   TEXT,
    ADD COLUMN IF NOT EXISTS barcode_signature TEXT;

-- 2) Fast-generation output columns (used by fast_generation_service)
ALTER TABLE public.invitations
    ADD COLUMN IF NOT EXISTS pdf_url  TEXT,
    ADD COLUMN IF NOT EXISTS zip_url  TEXT;

-- 3) Index for fast lookup by token (already exists but ensure)
CREATE INDEX IF NOT EXISTS idx_invitations_token_hash ON public.invitations(token);

-- ============================================================
-- DONE: All missing columns added.
-- ============================================================
