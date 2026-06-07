-- ============================================================
-- Migration V9: Add event_address element type
-- إضافة نوع عنصر عنوان المكان لمحرر التصميم
-- ============================================================

-- Add 'event_address' to the element_type enum
ALTER TYPE public.element_type ADD VALUE IF NOT EXISTS 'event_address';
