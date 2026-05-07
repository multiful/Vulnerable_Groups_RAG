# File: upload_candidates_to_supabase.py
# Last Updated: 2026-05-07
# Content Hash: SHA256:TBD
# Role: cert_candidates.jsonl의 text_for_dense를 OpenAI 임베딩 → Supabase pgvector 업로드
#
# 실행 전 준비:
#   1. Supabase SQL 에디터에서 docs/architecture/supabase_langchain.sql 실행
#   2. backend/.env에 SUPABASE_SERVICE_KEY 실제 값 입력
#   3. backend/.env에 OPENAI_API_KEY 입력
#
# 실행:
#   python scripts/upload_candidates_to_supabase.py
#   python scripts/upload_candidates_to_supabase.py --dry-run   # 임베딩 없이 구조 확인
#   python scripts/upload_candidates_to_supabase.py --limit 50  # 처음 50개만
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

# Load .env manually (no python-dotenv dependency assumption)
_ENV_FILE = _PROJECT_ROOT / "backend" / ".env"
def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        if key.strip() and key.strip() not in os.environ:
            os.environ[key.strip()] = val.strip()

_load_env(_ENV_FILE)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
TABLE_NAME = os.environ.get("SUPABASE_TABLE_NAME", "documents")
EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

_CANDIDATES_JSONL = _PROJECT_ROOT / "data/canonical/candidates/cert_candidates.jsonl"

BATCH_SIZE = 20  # OpenAI embeddings API 배치 크기
RATE_SLEEP = 0.5  # API 호출 간 대기(초)


def load_candidates() -> list[dict]:
    rows = []
    with _CANDIDATES_JSONL.open(encoding="utf-8") as f:
        for line in f:
            if s := line.strip():
                rows.append(json.loads(s))
    return rows


def build_documents(candidates: list[dict]) -> list[dict]:
    """cert_candidates → Supabase documents 형식 변환."""
    docs = []
    for c in candidates:
        text = (c.get("text_for_dense") or "").strip()
        if not text:
            continue
        cert_id = c.get("cert_id", "")
        cert_name = c.get("cert_name", "")
        doc_id = f"cand_{cert_id}"
        docs.append({
            "id": doc_id,
            "content": text,
            "metadata": {
                "cert_id": cert_id,
                "cert_name": cert_name,
                "source_type": "candidate",
                "primary_domain": c.get("primary_domain") or "",
                "cert_grade_tier": c.get("cert_grade_tier") or "",
                "related_jobs": (c.get("related_jobs") or [])[:5],
                "recommended_risk_stages": c.get("recommended_risk_stages") or [],
            },
        })
    return docs


def embed_batch(texts: list[str], client) -> list[list[float]]:
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def upload_to_supabase(docs: list[dict], dry_run: bool = False) -> None:
    from openai import OpenAI
    from supabase import create_client

    if not dry_run:
        if not SUPABASE_SERVICE_KEY or SUPABASE_SERVICE_KEY == "your_service_role_key_here":
            print("ERROR: SUPABASE_SERVICE_KEY가 설정되지 않았습니다.")
            print("  backend/.env에 실제 service_role 키를 입력하세요.")
            print("  Supabase 대시보드 → Project Settings → API → service_role")
            sys.exit(1)
        if not OPENAI_API_KEY:
            print("ERROR: OPENAI_API_KEY가 설정되지 않았습니다.")
            sys.exit(1)
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    total = len(docs)
    print(f"업로드 대상: {total}개 문서 (테이블: {TABLE_NAME})")
    if dry_run:
        print("[DRY-RUN] 임베딩/업로드 건너뜀. 첫 3개 문서 구조 확인:")
        for d in docs[:3]:
            print(f"  id={d['id']}")
            print(f"  content={d['content'][:100]}...")
            print(f"  metadata={d['metadata']}")
        return

    uploaded = 0
    skipped = 0
    for batch_start in range(0, total, BATCH_SIZE):
        batch = docs[batch_start: batch_start + BATCH_SIZE]
        texts = [d["content"] for d in batch]

        try:
            embeddings = embed_batch(texts, openai_client)
        except Exception as e:
            print(f"  임베딩 오류 (batch {batch_start}~): {e}")
            skipped += len(batch)
            continue

        rows_to_insert = [
            {
                "id": d["id"],
                "content": d["content"],
                "metadata": d["metadata"],
                "embedding": emb,
            }
            for d, emb in zip(batch, embeddings)
        ]

        try:
            # upsert: 동일 id 재실행 시 덮어쓰기 (멱등)
            sb.table(TABLE_NAME).upsert(rows_to_insert).execute()
            uploaded += len(batch)
        except Exception as e:
            print(f"  Supabase 업로드 오류 (batch {batch_start}~): {e}")
            skipped += len(batch)
            continue

        pct = (batch_start + len(batch)) / total * 100
        print(f"  [{pct:5.1f}%] 업로드 완료: {batch_start + 1}~{batch_start + len(batch)}")
        time.sleep(RATE_SLEEP)

    print(f"\n완료: {uploaded}개 업로드, {skipped}개 실패")


def main() -> None:
    parser = argparse.ArgumentParser(description="cert_candidates → Supabase pgvector 업로드")
    parser.add_argument("--dry-run", action="store_true", help="임베딩/업로드 없이 구조 확인만")
    parser.add_argument("--limit", type=int, default=0, help="처음 N개만 처리 (0=전체)")
    args = parser.parse_args()

    if not _CANDIDATES_JSONL.exists():
        print(f"ERROR: {_CANDIDATES_JSONL} 없음. scripts/build_cert_candidates.py 먼저 실행.")
        sys.exit(1)

    candidates = load_candidates()
    print(f"cert_candidates.jsonl 로드: {len(candidates)}개")

    docs = build_documents(candidates)
    print(f"text_for_dense 있는 문서: {len(docs)}개")

    if args.limit > 0:
        docs = docs[: args.limit]
        print(f"--limit {args.limit} 적용: {len(docs)}개만 처리")

    upload_to_supabase(docs, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
