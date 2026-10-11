-- ====================================================================
-- SKRYPT SQL DLA SUPABASE (Skopiuj i wklej w Supabase -> SQL Editor)
-- ====================================================================

-- 1. Tworzenie tabeli wpisów godzin pracy
CREATE TABLE IF NOT EXISTS public.work_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_date DATE NOT NULL,
    role_name TEXT NOT NULL,
    hourly_rate NUMERIC(10, 2) NOT NULL,
    hours_worked NUMERIC(6, 2) NOT NULL,
    total_earned NUMERIC(10, 2) NOT NULL,
    notes TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Indeks dla szybkiego filtrowania po datach i miesiącach
CREATE INDEX IF NOT EXISTS idx_work_entries_date ON public.work_entries (entry_date DESC);

-- 3. Włączenie Row Level Security (RLS)
ALTER TABLE public.work_entries ENABLE ROW LEVEL SECURITY;

-- 4. Polisa zezwalająca na odczyt, zapis, edycję i usuwanie przy użyciu publicznego anon key
DROP POLICY IF EXISTS "Zezwolenie na pelen dostep dla anon" ON public.work_entries;

CREATE POLICY "Zezwolenie na pelen dostep dla anon" 
ON public.work_entries 
FOR ALL 
TO anon, authenticated
USING (true) 
WITH CHECK (true);

-- 5. Komentarz pomocniczy
COMMENT ON TABLE public.work_entries IS 'Ewidencja godzin pracy, ról i wynagrodzeń w spinaczce i recepcji';
