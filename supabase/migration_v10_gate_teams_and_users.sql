-- Migration V10: Associate gates with teams and users

-- 1. Add team_id to event_gates
ALTER TABLE public.event_gates 
    ADD COLUMN IF NOT EXISTS team_id UUID REFERENCES public.teams(id) ON DELETE SET NULL;

-- 2. Create event_gate_users join table
CREATE TABLE IF NOT EXISTS public.event_gate_users (
    gate_id UUID REFERENCES public.event_gates(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (gate_id, user_id)
);
