-- 1. Fix Permissions
GRANT ALL ON public.profiles TO anon, authenticated, service_role;
GRANT ALL ON public.scan_results TO anon, authenticated, service_role;

-- 2. Fix Infinite Recursion in Profiles table policies
DROP POLICY IF EXISTS "Admin can read all profiles" ON public.profiles;
CREATE POLICY "Admin can read all profiles"
  ON public.profiles FOR SELECT
  TO authenticated
  USING ( (auth.jwt() -> 'app_metadata' ->> 'role') = 'admin' );

DROP POLICY IF EXISTS "Admin can insert profiles" ON public.profiles;
CREATE POLICY "Admin can insert profiles"
  ON public.profiles FOR INSERT
  TO authenticated
  WITH CHECK ( (auth.jwt() -> 'app_metadata' ->> 'role') = 'admin' );

DROP POLICY IF EXISTS "Admin can update profiles" ON public.profiles;
CREATE POLICY "Admin can update profiles"
  ON public.profiles FOR UPDATE
  TO authenticated
  USING ( (auth.jwt() -> 'app_metadata' ->> 'role') = 'admin' );

DROP POLICY IF EXISTS "Admin can delete profiles" ON public.profiles;
CREATE POLICY "Admin can delete profiles"
  ON public.profiles FOR DELETE
  TO authenticated
  USING ( (auth.jwt() -> 'app_metadata' ->> 'role') = 'admin' );

-- 3. Fix Infinite Recursion in Scan Results table policies
DROP POLICY IF EXISTS "Admin can read all scans" ON public.scan_results;
CREATE POLICY "Admin can read all scans"
  ON public.scan_results FOR SELECT
  TO authenticated
  USING ( (auth.jwt() -> 'app_metadata' ->> 'role') = 'admin' );

-- 4. Fix Infinite Recursion in Storage policies
DROP POLICY IF EXISTS "Admin can view all scan images" ON storage.objects;
CREATE POLICY "Admin can view all scan images"
  ON storage.objects FOR SELECT
  TO authenticated
  USING (
    bucket_id = 'scan-images'
    AND (auth.jwt() -> 'app_metadata' ->> 'role') = 'admin'
  );

-- 5. SET ADMIN ROLE (PENTING!)
-- Karena policy sekarang membaca dari app_metadata (bukan dari tabel profiles untuk mencegah infinite recursion),
-- Anda harus mengeset role 'admin' ke user yang Anda buat manual di Supabase Dashboard.
-- Silakan jalankan query di bawah ini (GANTI emailnya dengan email admin Anda):

-- UPDATE auth.users
-- SET raw_app_meta_data = raw_app_meta_data || '{"role": "admin"}'::jsonb
-- WHERE email = 'admin@kulitdetect.com';
