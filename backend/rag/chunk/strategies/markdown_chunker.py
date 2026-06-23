# Content Hash: SHA256:<AUTO_HASH_OR_TBD>
# Last Updated: 2026-04-13
# Role: Markdown 구조 기반 청킹 전략 — heading propagation + 문단 의미 청킹
"""
official_guide / faq / announcement 문서에 사용.

전략:
1. heading 블록이 나타나면 현재 청크를 flush하고 새 섹션 시작.
2. paragraph/list 블록을 누적하면서 max_tokens 초과 직전에 split.
3. 표 블록은 단독 청크로 생성 (행 분리 절대 금지).
4. 각 청크에 section_path와 짧은 section prefix를 부여한다.
"""
from __future__ import annotations

import hashlib
from dataclasses import replace

from ...parse.ir_schema import ParseBlock, ParseIR
from ..chunk_schema import ChunkConfig, ChunkMetadata, ChunkRecord
from ..token_utils import count_tokens, split_by_tokens


def _source_type_from_ir(ir: ParseIR) -> str:
    p = ir.parser_used
    if p == "html":
        return "html"
    if p == "docx":
        return "docx"
    return "pdf"


def chunk_with_markdown(
    ir: ParseIR,
    config: ChunkConfig,
    cert_id: str = "UNKNOWN",
    doc_type: str = "official_guide",
) -> list[ChunkRecord]:
    """ParseIR를 markdown-aware 전략으로 청킹한다."""
    records: list[ChunkRecord] = []
    seq = 0

    buffer_blocks: list[ParseBlock] = []
    current_section_path: list[str] = []

    def flush_buffer(section_path: list[str]) -> None:
        nonlocal seq
        if not buffer_blocks:
            return
        combined = "\n\n".join(b.text for b in buffer_blocks)
        prefix = _make_prefix(section_path)
        text_with_prefix = (prefix + combined) if prefix else combined

        token_count = count_tokens(text_with_prefix)
        if token_count <= config.max_tokens:
            _append_chunk(
                records, text_with_prefix, buffer_blocks, section_path,
                ir, config, cert_id, doc_type, seq
            )
            seq += 1
        else:
            # 분할 필요
            parts = split_by_tokens(combined, config.max_tokens - count_tokens(prefix), config.overlap_tokens)
            for part in parts:
                text_part = (prefix + part) if prefix else part
                if count_tokens(text_part) >= config.min_tokens:
                    _append_chunk(
                        records, text_part, buffer_blocks, section_path,
                        ir, config, cert_id, doc_type, seq
                    )
                    seq += 1
        buffer_blocks.clear()

    for block in ir.blocks:
        if block.block_type == "heading":
            # heading이 나타나면 버퍼 flush
            flush_buffer(current_section_path)
            current_section_path = list(block.section_path) + [block.text]
            # heading 자체는 버퍼에 넣지 않음 (section_path로 전파)

        elif block.block_type == "table":
            # 표 전에 버퍼 flush
            flush_buffer(current_section_path)
            # 표는 단독 청크
            prefix = _make_prefix(block.section_path or current_section_path)
            table_text = (prefix + block.text) if prefix else block.text
            if count_tokens(table_text) >= config.min_tokens:
                _append_chunk(
                    records, table_text, [block],
                    block.section_path or current_section_path,
                    ir, config, cert_id, doc_type, seq
                )
                seq += 1

        else:
            # paragraph / list / other
            # 버퍼 누적 전 토큰 체크
            test_combined = "\n\n".join(b.text for b in buffer_blocks + [block])
            prefix = _make_prefix(current_section_path)
            test_text = (prefix + test_combined) if prefix else test_combined

            if buffer_blocks and count_tokens(test_text) > config.max_tokens:
                flush_buffer(current_section_path)

            buffer_blocks.append(block)

    flush_buffer(current_section_path)
    return records


# ---------------------------------------------------------------------------
# 내부 유틸
# ---------------------------------------------------------------------------

def _make_prefix(section_path: list[str]) -> str:
    """섹션 경로를 짧은 prefix로 변환. 최대 3단계."""
    if not section_path:
        return ""
    truncated = section_path[-3:] if len(section_path) > 3 else section_path
    return " > ".join(truncated) + "\n"


def _make_chunk_id(doc_id: str, source_loc: str, seq: int) -> str:
    page = source_loc.replace("page:", "p") if source_loc else "p0"
    return f"{doc_id}_{page}_c{seq}"


def _compute_chunk_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _append_chunk(
    records: list[ChunkRecord],
    text: str,
    blocks: list[ParseBlock],
    section_path: list[str],
    ir: ParseIR,
    config: ChunkConfig,
    cert_id: str,
    doc_type: str,
    seq: int,
) -> None:
    source_loc = blocks[0].source_loc if blocks else ""
    chunk_id = _make_chunk_id(ir.doc_id, source_loc, seq)
    chunk_hash = _compute_chunk_hash(text)

    metadata = ChunkMetadata(
        cert_id=cert_id,
        source_type=_source_type_from_ir(ir),
        doc_type=doc_type,
        doc_id=ir.doc_id,
        chunk_id=chunk_id,
        chunk_hash=chunk_hash,
        section_path=list(section_path),
        source_loc=source_loc,
        doc_version=config.doc_version,
        chunk_seq=seq,
    )
    records.append(ChunkRecord(
        chunk_id=chunk_id,
        doc_id=ir.doc_id,
        text=text,
        metadata=metadata,
    ))
