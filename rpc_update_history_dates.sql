-- ============================================
-- Update History RPCs to support Date Filtering
-- Run this in Supabase SQL Editor
-- ============================================

CREATE OR REPLACE FUNCTION public.get_history_page(
  p_user_id UUID,
  p_is_admin BOOLEAN DEFAULT FALSE,
  p_filter TEXT DEFAULT 'all',
  p_offset INTEGER DEFAULT 0,
  p_limit INTEGER DEFAULT 20,
  p_worker_id UUID DEFAULT NULL,
  p_start_date TIMESTAMPTZ DEFAULT NULL,
  p_end_date TIMESTAMPTZ DEFAULT NULL
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
    AND (p_start_date IS NULL OR sr.created_at >= p_start_date)
    AND (p_end_date IS NULL OR sr.created_at <= p_end_date)
  ORDER BY sr.created_at DESC
  OFFSET GREATEST(p_offset, 0)
  LIMIT LEAST(GREATEST(p_limit, 1), 100);
$$;

CREATE OR REPLACE FUNCTION public.get_history_count(
  p_user_id UUID,
  p_is_admin BOOLEAN DEFAULT FALSE,
  p_filter TEXT DEFAULT 'all',
  p_worker_id UUID DEFAULT NULL,
  p_start_date TIMESTAMPTZ DEFAULT NULL,
  p_end_date TIMESTAMPTZ DEFAULT NULL
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
    )
    AND (p_start_date IS NULL OR sr.created_at >= p_start_date)
    AND (p_end_date IS NULL OR sr.created_at <= p_end_date);
$$;
