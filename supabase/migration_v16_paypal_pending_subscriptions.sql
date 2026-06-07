-- Migration v16: Add pending_subscriptions table for PayPal
-- This table stores temporary subscription agreements before user approval

CREATE TABLE IF NOT EXISTS pending_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL DEFAULT 'paypal',
    provider_agreement_id VARCHAR(255) NOT NULL,
    payer_email VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_pending_subscriptions_tenant_id ON pending_subscriptions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pending_subscriptions_agreement_id ON pending_subscriptions(provider_agreement_id);

-- Add updated_at trigger
CREATE OR REPLACE FUNCTION update_pending_subscriptions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_pending_subscriptions_updated_at
    BEFORE UPDATE ON pending_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_pending_subscriptions_updated_at();

COMMENT ON TABLE pending_subscriptions IS 'Stores temporary PayPal subscription agreements before user approval';
