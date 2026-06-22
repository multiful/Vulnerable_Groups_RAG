# Content Hash: SHA256:<AUTO_HASH_OR_TBD>
# Last Updated: 2026-04-13
# Role: PDF Parse → Chunk → Embed → Store 파이프라인 진입점
"""
사용법:
    PYTHONPATH=. python scripts/parse/run.py [옵션]

옵션:
    --pdf-dir       PDF 디렉토리 (기본: data/raw/pdf)
    --output-dir    출력 디렉토리 (기본: data/index_ready)
    --manifest      manifest 파일 경로 (기본: output-dir/metadata/pipeline_manifest.json)
    --cert-master   cert_master.csv 경로 (기본: data/raw/csv/cert_master.csv)
    --force         증분 무시, 전체 재처리
    --dry-run       프로파일링만 수행, 파싱/청킹 미수행
    --doc-id        특정 문서 doc_id만 처리
    --skip-embed    JSONL까지만 생성, Supabase 인제스트 스킵 (기본: True)
    --no-skip-embed Supabase 인제스트 포함 실행
    -v / --verbose  DEBUG 로그 출력
"""
from __future__ import annotations

import argparse
import io
import logging
import sys
from pathlib import Path

# Windows cp949 콘솔에서 한글/유니코드 출력 보장
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="PDF Parse → Chunk → (Embed) 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--pdf-dir", default="data/raw/pdf", help="PDF 파일 디렉토리")
    p.add_argument("--html-dir", default="data/raw/html", help="HTML 파일 디렉토리")
    p.add_argument("--docx-dir", default="data/raw/docx", help="DOCX 파일 디렉토리")
    p.add_argument("--output-dir", default="data/index_ready", help="출력 디렉토리")
    p.add_argument("--manifest", default=None, help="manifest JSON 경로")
    p.add_argument(
        "--cert-master",
        default="data/raw/csv/cert_master.csv",
        help="cert_master.csv 경로",
    )
    p.add_argument("--force", action="store_true", help="증분 무시 전체 재처리")
    p.add_argument("--dry-run", action="store_true", help="프로파일링만 수행")
    p.add_argument("--doc-id", default=None, help="특정 doc_id만 처리")
    p.add_argument(
        "--skip-embed",
        action="store_true",
        default=True,
        help="JSONL까지만 생성 (기본값)",
    )
    p.add_argument(
        "--no-skip-embed",
        dest="skip_embed",
        action="store_false",
        help="Supabase 인제스트 포함 실행",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="DEBUG 로그 출력")
    return p


def main() -> None:
    args = _build_parser().parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # PYTHONPATH 확인
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from backend.rag.pipeline.runner import PipelineOptions, run_pipeline

    options = PipelineOptions(
        pdf_dir=Path(args.pdf_dir),
        html_dir=Path(args.html_dir),
        docx_dir=Path(args.docx_dir),
        output_dir=Path(args.output_dir),
        manifest_path=Path(args.manifest) if args.manifest else None,
        cert_master_path=Path(args.cert_master),
        force=args.force,
        dry_run=args.dry_run,
        skip_embed=args.skip_embed,
        doc_id_filter=args.doc_id,
    )

    results = run_pipeline(options)

    # 결과 요약 출력
    print(f"\n{'='*60}")
    print(f"처리 결과: {len(results)}개 문서")
    total_chunks = 0
    for r in results:
        flags_str = f" [{', '.join(r.quality_flags)}]" if r.quality_flags else ""
        print(f"  {r.status:8} {r.doc_id:<40} chunks={r.chunk_count}{flags_str}")
        total_chunks += r.chunk_count

    done_count = sum(1 for r in results if r.status == "done")
    skip_count = sum(1 for r in results if r.status == "skipped")
    err_count = sum(1 for r in results if r.status == "error")

    print(f"\n완료={done_count} 스킵={skip_count} 오류={err_count} 총청크={total_chunks}")

    if err_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
