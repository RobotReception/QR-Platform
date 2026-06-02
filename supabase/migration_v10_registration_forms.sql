-- ============================================================
-- Migration V10: Event Self-Registration Forms
-- ============================================================

CREATE TABLE public.event_registration_forms (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                   UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    event_id                    UUID NOT NULL UNIQUE REFERENCES public.events(id) ON DELETE CASCADE,
    is_enabled                  BOOLEAN NOT NULL DEFAULT false,
    
    -- barcode_generation_mode: 'immediate' or 'deferred'
    barcode_generation_mode     TEXT NOT NULL DEFAULT 'immediate',
    
    -- default_ticket_class: 'normal' or 'vip'
    default_ticket_class        ticket_class NOT NULL DEFAULT 'normal',
    
    default_template_id         UUID REFERENCES public.invite_templates(id) ON DELETE SET NULL,
    
    -- Success and pending messages
    success_message_ar          TEXT DEFAULT 'تم تسجيلكم بنجاح! يمكنك تحميل بطاقتك الآن.',
    success_message_en          TEXT DEFAULT 'Registration successful! You can download your card now.',
    pending_approval_message_ar TEXT DEFAULT 'تم استلام طلبكم بنجاح وهو قيد المراجعة حالياً وسيتم إشعاركم فور القبول.',
    pending_approval_message_en TEXT DEFAULT 'Request received! It is under review and you will be notified upon approval.',
    
    -- Dynamic fields schema
    fields                      JSONB NOT NULL DEFAULT '[]',
    
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Trigger to update updated_at
CREATE TRIGGER trigger_event_registration_forms_updated_at 
    BEFORE UPDATE ON public.event_registration_forms 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Row Level Security (RLS)
ALTER TABLE public.event_registration_forms ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Members can view registration forms" ON public.event_registration_forms
    FOR SELECT USING (tenant_id IN (SELECT public.get_my_tenant_ids()));
    
CREATE POLICY "Admins can manage registration forms" ON public.event_registration_forms
    FOR ALL USING (public.is_admin_of(tenant_id));
