-- ============================================================
-- Migration V8: Slot Index for Dynamic Text Elements
-- ربط النصوص الديناميكية بمواقع الباركودات
-- ============================================================
-- Adds slot_index column to template_elements to link
-- dynamic_text elements to their corresponding barcode slot.
-- NULL = use default context (backward compatible)
-- 0, 1, 2, 3... = use slot_contexts[slot_index]
-- ============================================================

-- Alter enum element_type to include 'dynamic_text'
ALTER TYPE public.element_type ADD VALUE IF NOT EXISTS 'dynamic_text';

ALTER TABLE public.template_elements
    ADD COLUMN IF NOT EXISTS slot_index INTEGER DEFAULT NULL;

-- Optional constraint: slot_index must be non-negative when set
ALTER TABLE public.template_elements
    ADD CONSTRAINT chk_element_slot_index CHECK (slot_index IS NULL OR slot_index >= 0);

-- ============================================================
-- DONE: Migration V8 complete
-- ============================================================
