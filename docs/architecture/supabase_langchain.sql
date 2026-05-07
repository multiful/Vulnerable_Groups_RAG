-- File: supabase_langchain.sql
-- Last Updated: 2026-05-07
-- Content Hash: SHA256:TBD
-- Role: Supabase pgvector 스키마 + match_documents RPC
--
-- 임베딩 차원: OpenAI text-embedding-3-small → 1536
-- HuggingFace all-MiniLM-L6-v2 → 384 (vector(N) 값을 함께 변경)
--
-- 실행: Supabase 대시보드 → SQL 에디터에 전체 붙여넣기 후 실행
-- 재실행 안전: CREATE IF NOT EXISTS / CREATE OR REPLACE 사용
-- upsert 정책: upload_candidates_to_supabase.py가 id 기반 upsert 수행

-- 1. pgvector 확장 활성화
create extension if not exists vector;

-- 2. documents 테이블
create table if not exists documents (
  id        text primary key,
  content   text,
  metadata  jsonb default '{}'::jsonb,
  embedding vector(1536)
);

-- 3. cert_id 메타데이터 인덱스 (필터 검색 성능)
create index if not exists documents_cert_id_idx
  on documents ((metadata->>'cert_id'));

-- 4. 벡터 유사도 인덱스 (ivfflat, 1290개 문서 기준 lists=50 적당)
create index if not exists documents_embedding_idx
  on documents
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 50);

-- 5. match_documents RPC
--    query_embedding : 검색 벡터 (1536차원)
--    filter          : jsonb containment 필터 예: '{"cert_id": "cert_0001"}'
--    match_count     : 반환 최대 행 수 (기본 5)
create or replace function match_documents(
  query_embedding vector(1536),
  filter          jsonb    default null,
  match_count     int      default 5
)
returns table (
  id          text,
  content     text,
  metadata    jsonb,
  similarity  float8
)
language sql
stable
as $$
  select
    d.id,
    d.content,
    d.metadata,
    1 - (d.embedding <=> query_embedding) as similarity
  from documents d
  where
    filter is null
    or filter = '{}'::jsonb
    or d.metadata @> filter
  order by d.embedding <=> query_embedding
  limit match_count;
$$;
