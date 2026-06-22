# Content Hash: SHA256:<AUTO_HASH_OR_TBD>
# Last Updated: 2026-04-13
# Role: 파이프라인 오케스트레이터 — profiling → parse → chunk → cert_map → quality → JSONL
"""
run_pipeline(options): 전체 파이프라인 실행.
run_single_doc(pdf_path, options): 단일 문서 처리.

doc_type 매핑 규칙 (파일명 기반 휴리스틱):
    '시행일정' | '일정'  → schedule
    '통계'              → statistics
    '전단지' | '홍보'   → announcement
    'FAQ' | '자주'      → faq
    그 외               → official_guide
"""
from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PipelineOptions:
    """파이프라인 실행 옵션."""

    pdf_dir: Path = Path("data/raw/pdf")
    html_dir: Path = Path("data/raw/html")
    docx_dir: Path = Path("data/raw/docx")
    output_dir: Path = Path("data/index_ready")
    manifest_path: Optional[Path] = None
    cert_master_path: Path = Path("data/raw/csv/cert_master.csv")

    force: bool = False
    """True이면 증분 무시, 전체 재처리."""

    dry_run: bool = False
    """True이면 프로파일링만 수행, 파싱/청킹 미수행."""

    skip_embed: bool = True
    """True이면 JSONL까지만 생성, Supabase 인제스트 스킵."""

    doc_id_filter: Optional[str] = None
    """특정 doc_id만 처리. None이면 전체 처리."""


@dataclass
class DocProcessResult:
    """단일 문서 처리 결과."""

    doc_id: str
    status: str  # "done" | "skipped" | "error"
    parser_used: str = ""
    chunk_count: int = 0
    quality_flags: list[str] = field(default_factory=list)
    error: str = ""


def run_pipeline(options: PipelineOptions) -> list[DocProcessResult]:
    """전체 PDF 파이프라인을 실행한다."""
    from ..parse.profiler import profile_pdf
    from ..parse.router import describe_routing, route
    from .manifest import PipelineManifest

    # manifest 경로 결정
    manifest_path = options.manifest_path or (
        options.output_dir / "metadata" / "pipeline_manifest.json"
    )
    manifest = PipelineManifest.load(manifest_path)

    pdf_dir = options.pdf_dir
    pdf_files = sorted(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        logger.warning("No PDF files found in %s", pdf_dir)
        return []

    results: list[DocProcessResult] = []

    for pdf_path in pdf_files:
        try:
            profile = profile_pdf(pdf_path)

            if options.doc_id_filter and profile.doc_id != options.doc_id_filter:
                continue

            if options.dry_run:
                routing = describe_routing(profile)
                _print_dry_run(profile.doc_id, routing)
                results.append(DocProcessResult(
                    doc_id=profile.doc_id,
                    status="dry_run",
                    parser_used=routing["recommended_parser"],
                ))
                continue

            result = run_single_doc(pdf_path, options, manifest, profile=profile)
            results.append(result)

        except Exception as exc:
            logger.error("Error processing %s: %s", pdf_path.name, exc, exc_info=True)
            results.append(DocProcessResult(
                doc_id=pdf_path.stem[:80],
                status="error",
                error=str(exc),
            ))

    # HTML 파일 처리
    html_dir = options.html_dir
    html_files = sorted(html_dir.glob("*.html")) if html_dir.exists() else []

    for html_path in html_files:
        try:
            from ..parse.parsers.html_parser import compute_html_file_hash, slugify_html
            doc_id = slugify_html(html_path.name)

            if options.doc_id_filter and doc_id != options.doc_id_filter:
                continue

            if options.dry_run:
                print(f"\n{'='*60}")
                print(f"[DRY-RUN HTML] {doc_id}")
                print(f"  parser: html (BeautifulSoup)")
                results.append(DocProcessResult(
                    doc_id=doc_id,
                    status="dry_run",
                    parser_used="html",
                ))
                continue

            result = run_single_html_doc(html_path, options, manifest)
            results.append(result)

        except Exception as exc:
            logger.error("Error processing HTML %s: %s", html_path.name, exc, exc_info=True)
            results.append(DocProcessResult(
                doc_id=html_path.stem[:80],
                status="error",
                error=str(exc),
            ))

    # DOCX 파일 처리
    docx_dir = options.docx_dir
    docx_files = sorted(docx_dir.glob("*.docx")) if docx_dir.exists() else []

    for docx_path in docx_files:
        try:
            from ..parse.parsers.docx_parser import slugify_docx
            doc_id = slugify_docx(docx_path.name)

            if options.doc_id_filter and doc_id != options.doc_id_filter:
                continue

            if options.dry_run:
                print(f"\n{'='*60}")
                print(f"[DRY-RUN DOCX] {doc_id}")
                print(f"  parser: docx (python-docx)")
                results.append(DocProcessResult(
                    doc_id=doc_id,
                    status="dry_run",
                    parser_used="docx",
                ))
                continue

            result = run_single_docx_doc(docx_path, options, manifest)
            results.append(result)

        except Exception as exc:
            logger.error("Error processing DOCX %s: %s", docx_path.name, exc, exc_info=True)
            results.append(DocProcessResult(
                doc_id=docx_path.stem[:80],
                status="error",
                error=str(exc),
            ))

    if not options.dry_run:
        manifest.save(manifest_path)
        logger.info("Manifest saved → %s", manifest_path)

        if not options.skip_embed:
            _run_ingest(options)

    return results


def run_single_doc(
    pdf_path: Path,
    options: PipelineOptions,
    manifest=None,
    *,
    profile=None,
) -> DocProcessResult:
    """단일 PDF 문서를 파싱 → 청킹 → JSONL 저장한다."""
    from ..parse.profiler import compute_file_hash, profile_pdf
    from ..parse.router import route, get_ocr_pages
    from ..parse.parsers.pymupdf_parser import parse_with_pymupdf
    from ..parse.parsers.pdfplumber_parser import parse_with_pdfplumber
    from ..chunk.builder import build_chunks, select_strategy
    from ..chunk.cert_mapper import load_cert_lookup, map_cert_ids
    from ..chunk.chunk_schema import ChunkConfig
    from .manifest import PipelineManifest
    from .serializer import append_chunks_jsonl, write_chunks_jsonl
    from .quality_checker import check_chunk_quality

    manifest_path = options.manifest_path or (
        options.output_dir / "metadata" / "pipeline_manifest.json"
    )
    if manifest is None:
        manifest = PipelineManifest.load(manifest_path)

    if profile is None:
        profile = profile_pdf(pdf_path)

    doc_id = profile.doc_id
    file_hash = profile.file_hash
    quality_flags: list[str] = []

    # --- Stage 1: Parse 증분 체크 ---
    parse_ir_path = options.output_dir / "parse_ir" / f"{doc_id}.json"
    parse_ir = None

    if not options.force and not manifest.is_parse_stale(doc_id, file_hash):
        # 캐시된 ParseIR 로드
        parse_ir = _load_parse_ir(parse_ir_path)
        if parse_ir:
            logger.info("[%s] parse 스킵 (file_hash 동일)", doc_id)

    if parse_ir is None:
        # 파서 선택
        parser_name = route(profile)
        profile.recommended_parser = parser_name

        # OCR 필요 페이지 체크 (경고만, 현재 단계에서 OCR 처리 통합 안 함)
        ocr_pages = get_ocr_pages(profile)
        if ocr_pages:
            logger.warning(
                "[%s] OCR 필요 페이지: %s (page-level OCR 미적용)", doc_id, ocr_pages
            )
            quality_flags.append(f"ocr_needed_pages:{len(ocr_pages)}")

        logger.info("[%s] 파싱 시작 (parser=%s)", doc_id, parser_name)
        if parser_name == "pdfplumber":
            parse_ir = parse_with_pdfplumber(pdf_path, profile)
        else:
            parse_ir = parse_with_pymupdf(pdf_path, profile)

        quality_flags.extend(parse_ir.parse_quality_flags)

        # 고중복 문서 대상 추가 정규화: 빈 템플릿 표 제거 + 블록 레벨 중복 제거
        before = len(parse_ir.blocks)
        if "multi_column_detected" in quality_flags or parser_name == "pdfplumber":
            from ..parse.cleanup import remove_empty_tables, deduplicate_blocks
            parse_ir.blocks = remove_empty_tables(parse_ir.blocks)
            parse_ir.blocks = deduplicate_blocks(parse_ir.blocks)
            after = len(parse_ir.blocks)
            if after < before:
                logger.info("[%s] 블록 정규화: %d → %d (-%d)", doc_id, before, after, before - after)
                # parse_hash 재계산 (블록이 달라졌으므로)
                from ..parse.cleanup import compute_parse_hash
                parse_ir.parse_hash = compute_parse_hash(parse_ir.blocks)

        _save_parse_ir(parse_ir, parse_ir_path)
        logger.info("[%s] 파싱 완료: %d 블록", doc_id, len(parse_ir.blocks))

    # --- Stage 2: Chunk 증분 체크 ---
    doc_type = _infer_doc_type(pdf_path.name)
    config = ChunkConfig(
        max_tokens=512,
        overlap_tokens=64,
        min_tokens=20,
        doc_type=doc_type,
    )

    chunks_jsonl_path = options.output_dir / "chunks" / "chunks.jsonl"
    chunks = None

    if not options.force and not manifest.is_chunk_stale(doc_id, parse_ir.parse_hash):
        logger.info("[%s] chunk 스킵 (parse_hash 동일)", doc_id)
        doc_entry = manifest.documents.get(doc_id, {})
        return DocProcessResult(
            doc_id=doc_id,
            status="skipped",
            parser_used=parse_ir.parser_used,
            chunk_count=doc_entry.get("chunk_count", 0),
            quality_flags=quality_flags,
        )

    # cert_lookup 로드
    cert_lookup = load_cert_lookup(options.cert_master_path)

    logger.info("[%s] 청킹 시작 (strategy=%s, doc_type=%s)", doc_id, select_strategy(doc_type), doc_type)
    chunks = build_chunks(parse_ir, config)
    chunks = map_cert_ids(chunks, cert_lookup, doc_type, quality_flags=quality_flags)

    # 품질 검증
    report = check_chunk_quality(chunks, config)
    logger.info("[%s] 품질 검사: %s", doc_id, report.summary())
    quality_flags.extend(report.flags)

    # JSONL 저장 (첫 문서면 새로 쓰고 이후엔 append)
    if not chunks_jsonl_path.exists():
        written = write_chunks_jsonl(chunks, chunks_jsonl_path)
    else:
        written = append_chunks_jsonl(chunks, chunks_jsonl_path)
    logger.info("[%s] JSONL 저장: %d 청크 → %s", doc_id, written, chunks_jsonl_path)

    # manifest 갱신
    manifest.update_parse(
        doc_id=doc_id,
        file_hash=file_hash,
        parse_hash=parse_ir.parse_hash,
        parser_used=parse_ir.parser_used,
        chunk_count=len(chunks),
        quality_flags=quality_flags,
        status="done",
    )

    return DocProcessResult(
        doc_id=doc_id,
        status="done",
        parser_used=parse_ir.parser_used,
        chunk_count=len(chunks),
        quality_flags=quality_flags,
    )


def run_single_html_doc(
    html_path: Path,
    options: PipelineOptions,
    manifest=None,
) -> DocProcessResult:
    """단일 HTML 파일을 파싱 → 청킹 → JSONL 저장한다."""
    from ..parse.parsers.html_parser import (
        compute_html_file_hash,
        parse_with_html,
        slugify_html,
    )
    from ..chunk.builder import build_chunks, select_strategy
    from ..chunk.cert_mapper import load_cert_lookup, map_cert_ids
    from ..chunk.chunk_schema import ChunkConfig
    from .manifest import PipelineManifest
    from .serializer import append_chunks_jsonl, write_chunks_jsonl
    from .quality_checker import check_chunk_quality

    manifest_path = options.manifest_path or (
        options.output_dir / "metadata" / "pipeline_manifest.json"
    )
    if manifest is None:
        manifest = PipelineManifest.load(manifest_path)

    doc_id = slugify_html(html_path.name)
    file_hash = compute_html_file_hash(html_path)
    quality_flags: list[str] = []

    # --- Parse 증분 체크 ---
    parse_ir_path = options.output_dir / "parse_ir" / f"{doc_id}.json"
    parse_ir = None

    if not options.force and not manifest.is_parse_stale(doc_id, file_hash):
        parse_ir = _load_parse_ir(parse_ir_path)
        if parse_ir:
            logger.info("[%s] parse 스킵 (file_hash 동일)", doc_id)

    if parse_ir is None:
        logger.info("[%s] HTML 파싱 시작", doc_id)
        parse_ir = parse_with_html(html_path, doc_id=doc_id, file_hash=file_hash)
        _save_parse_ir(parse_ir, parse_ir_path)
        logger.info("[%s] HTML 파싱 완료: %d 블록", doc_id, len(parse_ir.blocks))

    # --- Chunk 증분 체크 ---
    doc_type = _infer_doc_type(html_path.name)
    config = ChunkConfig(
        max_tokens=512,
        overlap_tokens=64,
        min_tokens=20,
        doc_type=doc_type,
    )

    chunks_jsonl_path = options.output_dir / "chunks" / "chunks.jsonl"

    if not options.force and not manifest.is_chunk_stale(doc_id, parse_ir.parse_hash):
        logger.info("[%s] chunk 스킵 (parse_hash 동일)", doc_id)
        doc_entry = manifest.documents.get(doc_id, {})
        return DocProcessResult(
            doc_id=doc_id,
            status="skipped",
            parser_used="html",
            chunk_count=doc_entry.get("chunk_count", 0),
            quality_flags=quality_flags,
        )

    cert_lookup = load_cert_lookup(options.cert_master_path)

    logger.info("[%s] 청킹 시작 (strategy=%s, doc_type=%s)", doc_id, select_strategy(doc_type), doc_type)
    chunks = build_chunks(parse_ir, config)
    chunks = map_cert_ids(chunks, cert_lookup, doc_type, quality_flags=quality_flags)

    report = check_chunk_quality(chunks, config)
    logger.info("[%s] 품질 검사: %s", doc_id, report.summary())
    quality_flags.extend(report.flags)

    if not chunks_jsonl_path.exists():
        written = write_chunks_jsonl(chunks, chunks_jsonl_path)
    else:
        written = append_chunks_jsonl(chunks, chunks_jsonl_path)
    logger.info("[%s] JSONL 저장: %d 청크 → %s", doc_id, written, chunks_jsonl_path)

    manifest.update_parse(
        doc_id=doc_id,
        file_hash=file_hash,
        parse_hash=parse_ir.parse_hash,
        parser_used="html",
        chunk_count=len(chunks),
        quality_flags=quality_flags,
        status="done",
    )

    return DocProcessResult(
        doc_id=doc_id,
        status="done",
        parser_used="html",
        chunk_count=len(chunks),
        quality_flags=quality_flags,
    )


def run_single_docx_doc(
    docx_path: Path,
    options: PipelineOptions,
    manifest=None,
) -> DocProcessResult:
    """단일 DOCX 파일을 파싱 → 청킹 → JSONL 저장한다."""
    from ..parse.parsers.docx_parser import (
        compute_docx_file_hash,
        parse_with_docx,
        slugify_docx,
    )
    from ..chunk.builder import build_chunks, select_strategy
    from ..chunk.cert_mapper import load_cert_lookup, map_cert_ids
    from ..chunk.chunk_schema import ChunkConfig
    from .manifest import PipelineManifest
    from .serializer import append_chunks_jsonl, write_chunks_jsonl
    from .quality_checker import check_chunk_quality

    manifest_path = options.manifest_path or (
        options.output_dir / "metadata" / "pipeline_manifest.json"
    )
    if manifest is None:
        manifest = PipelineManifest.load(manifest_path)

    doc_id = slugify_docx(docx_path.name)
    file_hash = compute_docx_file_hash(docx_path)
    quality_flags: list[str] = []

    # --- Parse 증분 체크 ---
    parse_ir_path = options.output_dir / "parse_ir" / f"{doc_id}.json"
    parse_ir = None

    if not options.force and not manifest.is_parse_stale(doc_id, file_hash):
        parse_ir = _load_parse_ir(parse_ir_path)
        if parse_ir:
            logger.info("[%s] parse 스킵 (file_hash 동일)", doc_id)

    if parse_ir is None:
        logger.info("[%s] DOCX 파싱 시작", doc_id)
        parse_ir = parse_with_docx(docx_path, doc_id=doc_id, file_hash=file_hash)
        _save_parse_ir(parse_ir, parse_ir_path)
        logger.info("[%s] DOCX 파싱 완료: %d 블록", doc_id, len(parse_ir.blocks))

    # --- Chunk 증분 체크 ---
    doc_type = _infer_doc_type(docx_path.name)
    config = ChunkConfig(
        max_tokens=512,
        overlap_tokens=64,
        min_tokens=20,
        doc_type=doc_type,
    )

    chunks_jsonl_path = options.output_dir / "chunks" / "chunks.jsonl"

    if not options.force and not manifest.is_chunk_stale(doc_id, parse_ir.parse_hash):
        logger.info("[%s] chunk 스킵 (parse_hash 동일)", doc_id)
        doc_entry = manifest.documents.get(doc_id, {})
        return DocProcessResult(
            doc_id=doc_id,
            status="skipped",
            parser_used="docx",
            chunk_count=doc_entry.get("chunk_count", 0),
            quality_flags=quality_flags,
        )

    cert_lookup = load_cert_lookup(options.cert_master_path)

    logger.info("[%s] 청킹 시작 (strategy=%s, doc_type=%s)", doc_id, select_strategy(doc_type), doc_type)
    chunks = build_chunks(parse_ir, config)
    chunks = map_cert_ids(chunks, cert_lookup, doc_type, quality_flags=quality_flags)

    report = check_chunk_quality(chunks, config)
    logger.info("[%s] 품질 검사: %s", doc_id, report.summary())
    quality_flags.extend(report.flags)

    if not chunks_jsonl_path.exists():
        written = write_chunks_jsonl(chunks, chunks_jsonl_path)
    else:
        written = append_chunks_jsonl(chunks, chunks_jsonl_path)
    logger.info("[%s] JSONL 저장: %d 청크 → %s", doc_id, written, chunks_jsonl_path)

    manifest.update_parse(
        doc_id=doc_id,
        file_hash=file_hash,
        parse_hash=parse_ir.parse_hash,
        parser_used="docx",
        chunk_count=len(chunks),
        quality_flags=quality_flags,
        status="done",
    )

    return DocProcessResult(
        doc_id=doc_id,
        status="done",
        parser_used="docx",
        chunk_count=len(chunks),
        quality_flags=quality_flags,
    )


# ---------------------------------------------------------------------------
# 내부 유틸
# ---------------------------------------------------------------------------

def _infer_doc_type(filename: str) -> str:
    """파일명 기반 doc_type 휴리스틱 추정."""
    name_lower = filename.lower()
    if any(kw in name_lower for kw in ("시행일정", "일정", "schedule")):
        return "schedule"
    if any(kw in name_lower for kw in ("통계", "statistics", "연보")):
        return "statistics"
    if any(kw in name_lower for kw in ("전단지", "홍보", "flyer", "leaflet")):
        return "announcement"
    if any(kw in name_lower for kw in ("faq", "자주")):
        return "faq"
    return "official_guide"


def _save_parse_ir(parse_ir, path: Path) -> None:
    """ParseIR를 JSON 파일로 저장한다."""
    from dataclasses import asdict
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(parse_ir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_parse_ir(path: Path):
    """JSON 파일에서 ParseIR를 로드한다. 실패 시 None 반환."""
    if not path.exists():
        return None
    try:
        from ..parse.ir_schema import ParseBlock, ParseIR
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        blocks = [ParseBlock(**b) for b in data.pop("blocks", [])]
        return ParseIR(blocks=blocks, **data)
    except Exception as exc:
        logger.warning("ParseIR 로드 실패 (%s): %s", path, exc)
        return None


def _print_dry_run(doc_id: str, routing: dict) -> None:
    """dry-run 결과를 출력한다."""
    print(f"\n{'='*60}")
    print(f"[DRY-RUN] {doc_id}")
    print(f"  recommended_parser : {routing['recommended_parser']}")
    metrics = routing.get("metrics", {})
    for k, v in metrics.items():
        print(f"  {k:<20}: {v}")
    if routing.get("warnings"):
        for w in routing["warnings"]:
            print(f"  [!] {w}")


def _run_ingest(options: PipelineOptions) -> None:
    """backend.rag.ingest.cli를 subprocess로 호출한다."""
    import subprocess
    chunks_jsonl = options.output_dir / "chunks" / "chunks.jsonl"
    if not chunks_jsonl.exists():
        logger.warning("chunks.jsonl 없음 — ingest 스킵")
        return
    cmd = [sys.executable, "-m", "backend.rag.ingest.cli", "--chunks-file", str(chunks_jsonl)]
    logger.info("Supabase 인제스트 시작: %s", " ".join(cmd))
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        logger.error("Ingest CLI 종료 코드: %d", result.returncode)
    else:
        logger.info("Ingest 완료")
