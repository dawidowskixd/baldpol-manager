-- ====================================================================
-- SKRYPT SQL DLA SUPABASE
-- ====================================================================

CREATE TABLE IF NOT EXISTS public.work_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_date DATE NOT NULL,
    role_name TEXT NOT NULL,
    hourly_rate NUMERIC(10, 2) NOT NULL,
    hours_worked NUMERIC(6, 2) NOT NULL,
    bonus NUMERIC(10, 2) DEFAULT 0.0,
    total_earned NUMERIC(10, 2) NOT NULL,
    notes TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_work_entries_date ON public.work_entries (entry_date DESC);

ALTER TABLE public.work_entries ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Zezwolenie na pelen dostep dla anon" ON public.work_entries;

CREATE POLICY "Zezwolenie na pelen dostep dla anon" 
ON public.work_entries 
FOR ALL 
TO anon, authenticated
USING (true) 
WITH CHECK (true);
