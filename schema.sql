-- ============================================
-- KulitDetect Database Schema
-- Run this in Supabase SQL Editor (Dashboard)
-- ============================================

-- 1. PROFILES TABLE
-- Stores user metadata linked to Supabase Auth
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username TEXT UNIQUE NOT NULL,
  full_name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'pekerja' CHECK (role IN ('pekerja', 'admin')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Users can read own profile
CREATE POLICY "Users can read own profile"
  ON public.profiles FOR SELECT
  TO authenticated
  USING ((SELECT auth.uid()) = id);

-- Admin can read all profiles
CREATE POLICY "Admin can read all profiles"
  ON public.profiles FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = (SELECT auth.uid()) AND p.role = 'admin'
    )
  );

-- Admin can insert profiles (creating new users)
CREATE POLICY "Admin can insert profiles"
  ON public.profiles FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = (SELECT auth.uid()) AND p.role = 'admin'
    )
  );

-- Admin can update profiles
CREATE POLICY "Admin can update profiles"
  ON public.profiles FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = (SELECT auth.uid()) AND p.role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = (SELECT auth.uid()) AND p.role = 'admin'
    )
  );

-- Admin can delete profiles
CREATE POLICY "Admin can delete profiles"
  ON public.profiles FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = (SELECT auth.uid()) AND p.role = 'admin'
    )
  );


-- 2. SCAN RESULTS TABLE
CREATE TABLE public.scan_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  image_path TEXT NOT NULL,
  is_defect BOOLEAN NOT NULL,
  defect_type TEXT NOT NULL DEFAULT 'Tidak Ada',
  confidence REAL NOT NULL,
  model_version TEXT DEFAULT '1.0',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_scan_results_user ON public.scan_results(user_id);
CREATE INDEX idx_scan_results_created ON public.scan_results(created_at DESC);
CREATE INDEX idx_scan_results_user_defect_created ON public.scan_results(user_id, is_defect, created_at DESC);

CREATE OR REPLACE FUNCTION public.get_scan_stats(p_user_id UUID DEFAULT NULL)
RETURNS TABLE (
  total_scans BIGINT,
  total_defects BIGINT,
  total_normal BIGINT,
  defect_rate NUMERIC
)
LANGUAGE sql
STABLE
AS $$
  WITH stats AS (
    SELECT
      COUNT(*)::BIGINT AS total_scans,
      COUNT(*) FILTER (WHERE is_defect)::BIGINT AS total_defects
    FROM public.scan_results
    WHERE p_user_id IS NULL OR user_id = p_user_id
  )
  SELECT
    total_scans,
    total_defects,
    (total_scans - total_defects)::BIGINT AS total_normal,
    CASE
      WHEN total_scans = 0 THEN 0
      ELSE ROUND((total_defects::NUMERIC / total_scans::NUMERIC) * 100, 1)
    END AS defect_rate
  FROM stats;
$$;

ALTER TABLE public.scan_results ENABLE ROW LEVEL SECURITY;


CREATE OR REPLACE FUNCTION public.get_history_page(
  p_user_id UUID,
  p_is_admin BOOLEAN DEFAULT FALSE,
  p_filter TEXT DEFAULT 'all',
  p_offset INTEGER DEFAULT 0,
  p_limit INTEGER DEFAULT 20,
  p_worker_id UUID DEFAULT NULL
)
RETURNS TABLE (
  id UUID,
  filename TEXT,
  image_path TEXT,
  is_defect BOOLEAN,
  defect_type TEXT,
  confidence REAL,
  created_at TIMESTAMPTZ,
  user_id UUID,
  worker_name TEXT
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    sr.id,
    sr.filename,
    sr.image_path,
    sr.is_defect,
    sr.defect_type,
    sr.confidence,
    sr.created_at,
    sr.user_id,
    COALESCE(p.full_name, 'Unknown') AS worker_name
  FROM public.scan_results sr
  LEFT JOIN public.profiles p ON p.id = sr.user_id
  WHERE
    (
      (
        p_is_admin
        AND (p_worker_id IS NULL OR sr.user_id = p_worker_id)
      )
      OR (
        NOT p_is_admin
        AND sr.user_id = p_user_id
      )
    )
    AND (
      p_filter = 'all'
      OR (p_filter = 'ok' AND sr.is_defect = FALSE)
      OR (p_filter = 'defect' AND sr.is_defect = TRUE)
    )
  ORDER BY sr.created_at DESC
  OFFSET GREATEST(p_offset, 0)
  LIMIT LEAST(GREATEST(p_limit, 1), 100);
$$;
-- Workers can read own scans
CREATE POLICY "Workers can read own scans"
  ON public.scan_results FOR SELECT
  TO authenticated
  USING ((SELECT auth.uid()) = user_id);

-- Workers can insert own scans (via backend service role, but also direct)
CREATE POLICY "Workers can insert own scans"
  ON public.scan_results FOR INSERT
  TO authenticated
  WITH CHECK ((SELECT auth.uid()) = user_id);

-- Admin can read all scans
CREATE POLICY "Admin can read all scans"
  ON public.scan_results FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = (SELECT auth.uid()) AND p.role = 'admin'
    )
  );


-- 3. STORAGE BUCKET
INSERT INTO storage.buckets (id, name, public)
VALUES ('scan-images', 'scan-images', false)
ON CONFLICT (id) DO NOTHING;

-- Storage policies: authenticated users can upload to their own folder
CREATE POLICY "Users can upload scan images"
  ON storage.objects FOR INSERT
  TO authenticated
  WITH CHECK (
    bucket_id = 'scan-images'
    AND (storage.foldername(name))[1] = (SELECT auth.uid())::text
  );

-- Users can view own images
CREATE POLICY "Users can view own scan images"
  ON storage.objects FOR SELECT
  TO authenticated
  USING (
    bucket_id = 'scan-images'
    AND (storage.foldername(name))[1] = (SELECT auth.uid())::text
  );

-- Admin can view all images
CREATE POLICY "Admin can view all scan images"
  ON storage.objects FOR SELECT
  TO authenticated
  USING (
    bucket_id = 'scan-images'
    AND EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = (SELECT auth.uid()) AND p.role = 'admin'
    )
  );


-- 4. HELPER FUNCTION: Auto-update updated_at
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER on_profile_updated
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_updated_at();
CREATE OR REPLACE FUNCTION public.get_history_count(
  p_user_id UUID,
  p_is_admin BOOLEAN DEFAULT FALSE,
  p_filter TEXT DEFAULT 'all',
  p_worker_id UUID DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE sql
STABLE
AS $$
  SELECT COUNT(*)::BIGINT
  FROM public.scan_results sr
  WHERE
    (
      (
        p_is_admin
        AND (p_worker_id IS NULL OR sr.user_id = p_worker_id)
      )
      OR (
        NOT p_is_admin
        AND sr.user_id = p_user_id
      )
    )
    AND (
      p_filter = 'all'
      OR (p_filter = 'ok' AND sr.is_defect = FALSE)
      OR (p_filter = 'defect' AND sr.is_defect = TRUE)
    );
$$;
