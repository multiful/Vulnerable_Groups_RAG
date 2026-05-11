-- File: supabase_cert_video_cache.sql
-- Last Updated: 2026-05-12
-- Content Hash: SHA256:TBD
-- Role: F-11 관련 동영상 추천 캐시 테이블 (DATA_SCHEMA.md §6.12)
--
-- 실행: Supabase 대시보드 → SQL 에디터에 전체 붙여넣기 후 실행
-- 재실행 안전: CREATE IF NOT EXISTS 사용
-- 캐시 정책: TTL 30일, application 단에서 fetched_at 비교로 만료 판정

-- 1. cert_video_cache 테이블
create table if not exists cert_video_cache (
  cert_id            text primary key,
  cert_name          text not null,
  search_query       text not null,
  videos             jsonb not null default '[]'::jsonb,
  query_version      int  not null default 1,
  fetched_at         timestamptz not null default now(),
  quota_exceeded_at  timestamptz
);

-- 2. fetched_at 기준 TTL 조회용 인덱스
create index if not exists cert_video_cache_fetched_at_idx
  on cert_video_cache (fetched_at desc);

-- 3. 갱신 helper (선택). application 코드에서 upsert하므로 필수는 아님.
--    참고용 — 직접 SQL로 캐시 수동 무효화할 때 사용.
-- delete from cert_video_cache where fetched_at < now() - interval '30 days';
