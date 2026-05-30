-- migration_v8_optional_guest_whatsapp.sql
-- Adds an optional WhatsApp contact column to invitations.

ALTER TABLE public.invitations
ADD COLUMN IF NOT EXISTS guest_whatsapp TEXT;

CREATE INDEX IF NOT EXISTS idx_invitations_guest_whatsapp
ON public.invitations(guest_whatsapp);
