-- ============================================================
-- Migration V7: Platform Consistency Fixes
-- Ensures runtime behavior matches the invitations/check-in APIs.
-- ============================================================

-- Invalid scan attempts may not resolve to a known invitation yet.
ALTER TABLE public.checkins
    ALTER COLUMN invitation_id DROP NOT NULL;

